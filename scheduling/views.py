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

from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import NeyoReferenceValue
from scheduling.models import (
    FIELD_CODE_CALENDAR_STATUS,
    FIELD_CODE_CALENDAR_TYPE,
    NeyoCalendar,
)
from scheduling.serializers import NeyoCalendarEventSerializer, NeyoCalendarSerializer

# §21.3's worked example value_codes for a PERSONAL calendar's own type/status.
PERSONAL_CALENDAR_TYPE_VALUE_CODE = "PERSONAL"
ACTIVE_STATUS_VALUE_CODE = "ACTIVE"


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

        client_id = principal.client_id
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
        created = False
        if calendar is None:
            calendar = NeyoCalendar(
                client_id=client_id,
                calendar_type=calendar_type,
                external_owner_id=external_user_id,
                name="Personal",
                timezone=request.data.get("timezone", "UTC"),
                status=active_status,
                created_by=external_user_id,
            )
            calendar.full_clean()  # runs NeyoCalendar.clean() -> validate_reference_value()
            calendar.save()
            created = True

        serializer = NeyoCalendarSerializer(calendar)
        return Response(serializer.data, status=201 if created else 200)


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
