"""
§13 API surface — the two Calendar endpoints Step 1 needs: get-or-create a
user's PERSONAL calendar (§7.1), and list a calendar's events. This is the
backend half of "see values entered through [a real call] reflected in the
backend" — Step 4 of the plan points the widget's own client.js at these
instead of mockData.js, without needing either endpoint to change shape.

Both accept either credential — the project's DEFAULT_AUTHENTICATION_CLASSES
(core.authentication.NeyoClientApiKeyAuthentication AND
NeyoWidgetTokenAuthentication) apply unmodified here, unlike
core.views.WidgetTokenView, which deliberately narrows to the API key only.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import NeyoClientApiKeyAuthentication
from core.models import NeyoReferenceValue
from scheduling.models import (
    FIELD_CODE_CALENDAR_EVENT_STATUS,
    FIELD_CODE_CALENDAR_EVENT_VISIBILITY,
    FIELD_CODE_CALENDAR_STATUS,
    FIELD_CODE_CALENDAR_TYPE,
    FIELD_CODE_EVENT_TYPE_CATEGORY,
    FIELD_CODE_EVENT_TYPE_SCOPE,
    NeyoCalendar,
    NeyoCalendarEvent,
    NeyoEventType,
)
from scheduling.serializers import (
    BookCalendarSlotRequestSerializer,
    NeyoCalendarEventCreateSerializer,
    NeyoCalendarEventSerializer,
    NeyoCalendarSerializer,
)

# §21.3's worked example value_codes for a PERSONAL calendar's own type/status.
PERSONAL_CALENDAR_TYPE_VALUE_CODE = "PERSONAL"
ACTIVE_STATUS_VALUE_CODE = "ACTIVE"

# v1 defaults for POST /api/calendars/{id}/events/ — see
# NeyoCalendarEventCreateSerializer's docstring for why these are assigned
# server-side instead of being asked of the caller.
EVENT_STATUS_SCHEDULED_VALUE_CODE = "SCHEDULED"
EVENT_VISIBILITY_SHARED_DETAILS_VALUE_CODE = "SHARED_DETAILS"
EVENT_TYPE_SCOPE_CLIENT_VALUE_CODE = "CLIENT"
GENERAL_EVENT_TYPE_CODE = "GENERAL"

# BookCalendarSlotView's own defaults — kept separate from the GENERAL ones
# above even though they overlap conceptually, so each endpoint's constants
# can diverge later without the other silently changing.
TOUR_EVENT_TYPE_CODE = "TOUR"  # matches the architecture doc's own §21.3 worked example
EVENT_TYPE_CATEGORY_SHOWING_VALUE_CODE = "SHOWING"


class SlotConflict(exceptions.APIException):
    """A real 409 — DRF's APIException defaults to 500 unless status_code is
    set explicitly. Raised by BookCalendarSlotView when the requested window
    overlaps an existing, non-cancelled event on the host's calendar."""

    status_code = 409
    default_detail = "That time is no longer available. Please pick another slot."
    default_code = "slot_conflict"


def _ensure_personal_calendar(*, client_id, external_user_id, timezone="UTC"):
    """Get-or-create a PERSONAL calendar for (client_id, external_user_id) —
    the same idempotent logic EnsurePersonalCalendarView.post() has always
    used, factored out so BookCalendarSlotView below can reuse it exactly
    rather than re-deriving it. Raises exceptions.APIException if the
    client's CALENDAR_TYPE=PERSONAL/CALENDAR_STATUS=ACTIVE reference rows
    don't exist yet, same as before."""
    try:
        calendar_type = NeyoReferenceValue.objects.get(
            client_id=client_id,
            field_code=FIELD_CODE_CALENDAR_TYPE,
            value_code=PERSONAL_CALENDAR_TYPE_VALUE_CODE,
            is_active=True,
        )
        active_status = NeyoReferenceValue.objects.get(
            client_id=client_id,
            field_code=FIELD_CODE_CALENDAR_STATUS,
            value_code=ACTIVE_STATUS_VALUE_CODE,
            is_active=True,
        )
    except NeyoReferenceValue.DoesNotExist:
        raise exceptions.APIException(
            f"client_id={client_id!r} has no active "
            f"{FIELD_CODE_CALENDAR_TYPE}={PERSONAL_CALENDAR_TYPE_VALUE_CODE!r} and/or "
            f"{FIELD_CODE_CALENDAR_STATUS}={ACTIVE_STATUS_VALUE_CODE!r} NeyoReferenceValue "
            f"row yet — seed those via /admin/ first (§2.7 Step 5)."
        )

    calendar = NeyoCalendar.objects.filter(
        client_id=client_id,
        calendar_type=calendar_type,
        external_owner_id=external_user_id,
    ).first()
    if calendar is None:
        calendar = NeyoCalendar(
            client_id=client_id,
            calendar_type=calendar_type,
            external_owner_id=external_user_id,
            name="Personal",
            timezone=timezone,
            status=active_status,
            created_by=external_user_id,
        )
        calendar.full_clean()  # runs NeyoCalendar.clean() -> validate_reference_value()
        calendar.save()
    return calendar


class EnsurePersonalCalendarView(APIView):
    """
    POST /api/calendars/personal/ensure/ — §7.1/§13/§20.2 point 6.

    Idempotent get-or-create, scoped to the authenticated principal's
    client_id. `external_user_id` comes from the widget token when present
    (a widget never gets to say whose calendar it wants); a client-API-key
    caller (server-to-server, no single end user baked into that
    credential) must supply it explicitly in the body.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        principal = request.user
        external_user_id = principal.external_user_id or request.data.get("external_user_id")
        if not external_user_id:
            raise exceptions.ValidationError(
                {"external_user_id": "Required when authenticated with a client API key."}
            )

        existing = NeyoCalendar.objects.filter(
            client_id=principal.client_id,
            calendar_type__value_code=PERSONAL_CALENDAR_TYPE_VALUE_CODE,
            calendar_type__field_code=FIELD_CODE_CALENDAR_TYPE,
            external_owner_id=external_user_id,
        ).exists()

        calendar = _ensure_personal_calendar(
            client_id=principal.client_id,
            external_user_id=external_user_id,
            timezone=request.data.get("timezone", "UTC"),
        )
        serializer = NeyoCalendarSerializer(calendar)
        return Response(serializer.data, status=200 if existing else 201)


class CalendarEventsView(APIView):
    """
    GET /api/calendars/{id}/events/ — §13, with the `persona_context` filter
    §13 documents ("display/filtering only, resolved server-side... never a
    second authorization boundary" — ARCH_043). Scoped to the authenticated
    principal's client_id first (§13): a calendar belonging to a different
    client_id 404s, it never leaks a cross-client "forbidden."
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, calendar_id):
        principal = request.user
        try:
            calendar = NeyoCalendar.objects.get(id=calendar_id, client_id=principal.client_id)
        except NeyoCalendar.DoesNotExist:
            raise exceptions.NotFound("No calendar with that id for this client.")

        events = calendar.events.all().order_by("start_at")

        persona_context = request.query_params.get("persona_context")
        if persona_context:
            codes = [code.strip() for code in persona_context.split(",") if code.strip()]
            if codes:
                events = events.filter(persona_context__value_code__in=codes)

        serializer = NeyoCalendarEventSerializer(events, many=True)
        return Response(serializer.data)

    def post(self, request, calendar_id):
        """
        POST /api/calendars/{id}/events/ — create an event on this calendar
        (§7.4). Same collection URL as the GET above (REST convention: GET
        lists, POST creates), same auth, same client_id scoping/404 rule.

        `created_by` comes from the widget token's external_user_id when
        present, same pattern as EnsurePersonalCalendarView.post() above; a
        client-API-key caller must supply it explicitly in the body.
        """
        principal = request.user
        try:
            calendar = NeyoCalendar.objects.get(id=calendar_id, client_id=principal.client_id)
        except NeyoCalendar.DoesNotExist:
            raise exceptions.NotFound("No calendar with that id for this client.")

        created_by = principal.external_user_id or request.data.get("external_user_id")
        if not created_by:
            raise exceptions.ValidationError(
                {"external_user_id": "Required when authenticated with a client API key."}
            )

        input_serializer = NeyoCalendarEventCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        client_id = principal.client_id
        status_ref, _ = NeyoReferenceValue.objects.get_or_create(
            client_id=client_id,
            field_code=FIELD_CODE_CALENDAR_EVENT_STATUS,
            value_code=EVENT_STATUS_SCHEDULED_VALUE_CODE,
        )
        visibility_ref, _ = NeyoReferenceValue.objects.get_or_create(
            client_id=client_id,
            field_code=FIELD_CODE_CALENDAR_EVENT_VISIBILITY,
            value_code=EVENT_VISIBILITY_SHARED_DETAILS_VALUE_CODE,
        )
        scope_ref, _ = NeyoReferenceValue.objects.get_or_create(
            client_id=client_id,
            field_code=FIELD_CODE_EVENT_TYPE_SCOPE,
            value_code=EVENT_TYPE_SCOPE_CLIENT_VALUE_CODE,
        )
        event_type, _ = NeyoEventType.objects.get_or_create(
            client_id=client_id,
            code=GENERAL_EVENT_TYPE_CODE,
            defaults={"name": "General", "scope": scope_ref},
        )

        event = NeyoCalendarEvent(
            calendar=calendar,
            event_type=event_type,
            status=status_ref,
            visibility=visibility_ref,
            created_by=created_by,
            **input_serializer.validated_data,
        )
        try:
            event.full_clean()
        except DjangoValidationError as exc:
            # full_clean() raises Django's own ValidationError, which DRF's
            # exception handler doesn't auto-convert to a 400 — left
            # uncaught, a bad request (e.g. end_at <= start_at) would leak
            # out as an unhandled 500 instead of a clean validation error.
            raise exceptions.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        event.save()

        return Response(NeyoCalendarEventSerializer(event).data, status=201)


class BookCalendarSlotView(APIView):
    """
    POST /api/calendars/book-slot/

    A deliberately minimal v1 slice of what the architecture doc specs out
    as the full Phase 1D booking lifecycle — NeyoBookingRequest,
    NeyoAvailabilityRule, NeyoAvailabilityException, NeyoSchedulingPolicy,
    NeyoBookingRequestHistory (that doc's §7.6-§7.9, §9). None of those
    models exist yet; building them is days of work (host-confirmation
    workflow, recurring availability windows, notice/buffer policy
    resolution order), not this pass. What this endpoint does instead,
    confirmed with the user before being built this way: if the requested
    window is free on the host's own PERSONAL calendar, book it immediately
    as a real NeyoCalendarEvent — no approval step, no availability-window
    checking (any time can be requested), just a real conflict check against
    whatever's already on that calendar.

    Concurrency safety (§9.2's own standard: "a lock on an unrelated row
    does not prevent two concurrent requests from reserving the same empty
    slot... tested against PostgreSQL"): the host's NeyoCalendar row is
    locked with select_for_update() inside one transaction, so a second
    concurrent request for the same host queues behind the first until it
    commits — the overlap check and the event creation it guards can never
    be split by a race. Tested with real concurrent requests against
    PostgreSQL, not just unit-tested serially — see the session's own
    concurrency smoke test.

    Interface-Layer-only, like core.views.WidgetTokenView: the caller here
    is always UN's own server (holding the long-lived key), relaying a
    request from a renter it has ALREADY authenticated and identified on
    its own side — never a browser-held widget token, which would let any
    logged-in widget session claim to book a slot on someone else's behalf
    using someone else's external_user_id as requester.
    """

    authentication_classes = [NeyoClientApiKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        input_serializer = BookCalendarSlotRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        if data["end_at"] <= data["start_at"]:
            raise exceptions.ValidationError({"end_at": "Must be after start_at."})

        client_id = request.user.client_id

        with transaction.atomic():
            calendar = _ensure_personal_calendar(
                client_id=client_id,
                external_user_id=data["host_external_user_id"],
                timezone=data["timezone"],
            )
            # Re-fetch under FOR UPDATE to actually hold the row lock for
            # the rest of this transaction — _ensure_personal_calendar's own
            # lookup above doesn't lock anything by itself.
            NeyoCalendar.objects.select_for_update().get(pk=calendar.pk)

            conflict_exists = (
                calendar.events.filter(start_at__lt=data["end_at"], end_at__gt=data["start_at"])
                .exclude(status__value_code="CANCELLED")
                .exists()
            )
            if conflict_exists:
                raise SlotConflict()

            status_ref, _ = NeyoReferenceValue.objects.get_or_create(
                client_id=client_id,
                field_code=FIELD_CODE_CALENDAR_EVENT_STATUS,
                value_code=EVENT_STATUS_SCHEDULED_VALUE_CODE,
            )
            visibility_ref, _ = NeyoReferenceValue.objects.get_or_create(
                client_id=client_id,
                field_code=FIELD_CODE_CALENDAR_EVENT_VISIBILITY,
                value_code=EVENT_VISIBILITY_SHARED_DETAILS_VALUE_CODE,
            )
            scope_ref, _ = NeyoReferenceValue.objects.get_or_create(
                client_id=client_id,
                field_code=FIELD_CODE_EVENT_TYPE_SCOPE,
                value_code=EVENT_TYPE_SCOPE_CLIENT_VALUE_CODE,
            )
            category_ref, _ = NeyoReferenceValue.objects.get_or_create(
                client_id=client_id,
                field_code=FIELD_CODE_EVENT_TYPE_CATEGORY,
                value_code=EVENT_TYPE_CATEGORY_SHOWING_VALUE_CODE,
            )
            event_type, _ = NeyoEventType.objects.get_or_create(
                client_id=client_id,
                code=TOUR_EVENT_TYPE_CODE,
                defaults={"name": "Property Tour", "scope": scope_ref, "category": category_ref},
            )

            event = NeyoCalendarEvent(
                calendar=calendar,
                event_type=event_type,
                status=status_ref,
                visibility=visibility_ref,
                created_by=data["requester_external_user_id"],
                title=f"Tour: {data['subject_title']}" if data["subject_title"] else "Property Tour",
                description=data["description"],
                start_at=data["start_at"],
                end_at=data["end_at"],
                timezone=data["timezone"],
                subject_title=data["subject_title"],
                subject_subtitle=data["subject_subtitle"],
            )
            try:
                event.full_clean()
            except DjangoValidationError as exc:
                raise exceptions.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
            event.save()

        return Response(NeyoCalendarEventSerializer(event).data, status=201)
