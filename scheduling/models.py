"""
`scheduling` — the Calendar module (Phase 1C of the architecture doc).

Named `scheduling`, not `calendar` — Python's own standard library already has a
`calendar` module, and naming a Django app the same thing risks `import calendar`
elsewhere in this project silently resolving to this app instead of the stdlib
module. "Scheduling" also matches the architecture doc's own title ("Calendar &
Scheduling") so nothing is lost by avoiding the collision.

Real models, built against calendar-scheduling/UrbanNest_CalendarScheduling_Architecture.md
§7.1–§7.5 (not §5–§6 — that earlier placeholder's section reference was wrong;
§5 is the Notification model, §6 is Conversation/Messaging, Calendar & Scheduling
is §7). Five models here: NeyoCalendar (§7.1), NeyoCalendarMembership (§7.2),
NeyoEventType (§7.3), NeyoCalendarEvent (§7.4), NeyoEventParticipant (§7.5).

FIELD-MAPPING PARITY WITH THE FRONTEND (explicit cross-check, done before writing
these models, not assumed): every field the already-built widget FE
(Neyora-FrontEnd/src/Calendar/, src/Events/, src/api/mockData.js, src/api/client.js)
actually reads has a same-named field below.

  src/api/mockData.js → mockCalendars:
    id, client_id, name, calendar_type, external_owner_id, account_id, property,
    timezone, status — all present on NeyoCalendar below.

  src/api/mockData.js → mockEventTypes:
    id, code, name, category — all present on NeyoEventType below (plus
    client_id/scope/account_id/is_active/created_at, which the FE doesn't
    render but the architecture doc requires).

  src/api/mockData.js → mockEvents (consumed by CalendarScreen.jsx, MonthView.jsx,
  AgendaView.jsx, Events/EventDetailPanel.jsx):
    id, calendar, event_type, title, description, start_at, end_at, timezone,
    status, visibility, persona_context, is_all_day, conferencing_url, location,
    subject_title, subject_subtitle, subject_image_url, subject_highlights,
    subject_actions — all present on NeyoCalendarEvent below. (`notes`,
    `created_by`/`updated_by`, `created_at`/`updated_at` are architecture-doc
    fields the FE never reads — that's expected, they're audit/internal fields,
    not a parity gap.)

  NeyoCalendarMembership and NeyoEventParticipant: not consumed by any FE file
  yet (no membership list is rendered; EventDetailPanel.jsx's Accept/Decline
  buttons are still hardcoded, not wired to `NeyoEventParticipant.response_status`).
  Built anyway — they're §7.2/§7.5 of the frozen architecture and the "Calendar
  module" the user asked for real models for, not just the subset the FE
  currently exercises.

Every choice-shaped field is an FK to core.NeyoReferenceValue (ARCH_042), never
a plain CharField `choices=`. Each one is validated in the owning model's
`clean()` via core.models.validate_reference_value(), against the field_code
constants below.
"""

from django.core.exceptions import ValidationError
from django.db import models

from core.models import NeyoReferenceValue, validate_reference_value

# field_code constants — the NeyoReferenceValue rows each FK below is allowed to
# point at. Mirrors the pattern already used for NeyoNotification.notification_type
# (field_code='NOTIFICATION_TYPE', architecture doc §5.3/§5.4). Not an exhaustive
# system-wide registry — just this app's own slice of it.
FIELD_CODE_CALENDAR_TYPE = "CALENDAR_TYPE"                      # §7.1 — PERSONAL/TEAM/PROPERTY
FIELD_CODE_CALENDAR_STATUS = "CALENDAR_STATUS"                  # §7.1 — ACTIVE/ARCHIVED
FIELD_CODE_CALENDAR_ACCESS_LEVEL = "CALENDAR_ACCESS_LEVEL"      # §7.2 — VIEW/EDIT/MANAGE
FIELD_CODE_CALENDAR_MEMBERSHIP_STATUS = "CALENDAR_MEMBERSHIP_STATUS"  # §7.2 — ACTIVE/REVOKED
FIELD_CODE_EVENT_TYPE_SCOPE = "EVENT_TYPE_SCOPE"                # §7.3/ARCH_061 — PLATFORM/CLIENT/ACCOUNT
FIELD_CODE_EVENT_TYPE_CATEGORY = "EVENT_TYPE_CATEGORY"          # §7.3/ARCH_058 — SHOWING/INSPECTION/MAINTENANCE/MEETING/OTHER
FIELD_CODE_CALENDAR_EVENT_STATUS = "CALENDAR_EVENT_STATUS"      # §7.4 — SCHEDULED/CANCELLED/COMPLETED
FIELD_CODE_CALENDAR_EVENT_VISIBILITY = "CALENDAR_EVENT_VISIBILITY"  # §7.4 — PRIVATE/BUSY_FREE/SHARED_DETAILS
FIELD_CODE_PERSONA_CONTEXT = "PERSONA_CONTEXT"                  # §7.4/ARCH_043 — display/filter only, never auth
FIELD_CODE_EVENT_PARTICIPANT_ROLE = "EVENT_PARTICIPANT_ROLE"    # §7.5 — ORGANIZER/ATTENDEE/ASSIGNEE
FIELD_CODE_EVENT_PARTICIPANT_RESPONSE_STATUS = "EVENT_PARTICIPANT_RESPONSE_STATUS"  # §7.5 — PENDING/ACCEPTED/DECLINED


class NeyoCalendar(models.Model):
    """
    Architecture doc §7.1.

    One active PERSONAL calendar per external_owner_id, shared across every
    persona that user holds (ARCH_043) — created lazily via
    POST /api/calendars/personal/ensure/, idempotent on repeated calls.
    account_id is always null for PERSONAL (ARCH_043) and only ever set for
    TEAM/PROPERTY (ARCH_061, §2.4).
    """

    id = models.BigAutoField(primary_key=True)
    client_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255)

    calendar_type = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendars_by_type",
        limit_choices_to={"field_code": FIELD_CODE_CALENDAR_TYPE},
    )

    # Conditional per calendar_type (§7.1): set for PERSONAL only.
    external_owner_id = models.CharField(max_length=128, null=True, blank=True)

    # Set for TEAM/PROPERTY only — always null for PERSONAL (ARCH_043, ARCH_061).
    account_id = models.CharField(max_length=128, null=True, blank=True)

    # Conditional per calendar_type (§7.1): set for PROPERTY only.
    property = models.CharField(max_length=128, null=True, blank=True)

    timezone = models.CharField(max_length=64)

    status = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendars_by_status",
        limit_choices_to={"field_code": FIELD_CODE_CALENDAR_STATUS},
    )

    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["client_id", "calendar_type"]),
            models.Index(fields=["client_id", "external_owner_id"]),
        ]

    def __str__(self):
        return f"NeyoCalendar(id={self.id}, name={self.name!r})"

    def clean(self):
        super().clean()
        if self.calendar_type_id:
            validate_reference_value(
                self.calendar_type, field_code=FIELD_CODE_CALENDAR_TYPE, client_id=self.client_id
            )
        if self.status_id:
            validate_reference_value(
                self.status, field_code=FIELD_CODE_CALENDAR_STATUS, client_id=self.client_id
            )


class NeyoCalendarMembership(models.Model):
    """Architecture doc §7.2. A revoked membership loses access immediately."""

    id = models.BigAutoField(primary_key=True)
    calendar = models.ForeignKey(NeyoCalendar, on_delete=models.CASCADE, related_name="memberships")
    external_user_id = models.CharField(max_length=128)

    access_level = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendar_memberships_by_access_level",
        limit_choices_to={"field_code": FIELD_CODE_CALENDAR_ACCESS_LEVEL},
    )
    status = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendar_memberships_by_status",
        limit_choices_to={"field_code": FIELD_CODE_CALENDAR_MEMBERSHIP_STATUS},
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "external_user_id"], name="uniq_calendarmembership_calendar_user"
            )
        ]

    def __str__(self):
        return f"NeyoCalendarMembership(calendar_id={self.calendar_id}, user={self.external_user_id})"

    def clean(self):
        super().clean()
        client_id = self.calendar.client_id if self.calendar_id else None
        if self.access_level_id and client_id:
            validate_reference_value(
                self.access_level, field_code=FIELD_CODE_CALENDAR_ACCESS_LEVEL, client_id=client_id
            )
        if self.status_id and client_id:
            validate_reference_value(
                self.status, field_code=FIELD_CODE_CALENDAR_MEMBERSHIP_STATUS, client_id=client_id
            )


class NeyoEventType(models.Model):
    """
    Architecture doc §7.3.

    `category` (ARCH_058) is a second, independent axis from `scope` — display/
    filter grouping only, never authorization. Matches
    Neyora-FrontEnd/src/Calendar/MyCalendarsNav.jsx's CATEGORY_LABELS exactly
    (SHOWING/INSPECTION/MAINTENANCE/MEETING/OTHER).
    """

    id = models.BigAutoField(primary_key=True)
    client_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64)

    scope = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="event_types_by_scope",
        limit_choices_to={"field_code": FIELD_CODE_EVENT_TYPE_SCOPE},
    )

    # Set only when scope="ACCOUNT" — always null for PLATFORM/CLIENT (ARCH_061, §2.4).
    account_id = models.CharField(max_length=128, null=True, blank=True)

    category = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="event_types_by_category",
        limit_choices_to={"field_code": FIELD_CODE_EVENT_TYPE_CATEGORY},
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["client_id", "code"])]

    def __str__(self):
        return f"NeyoEventType(code={self.code!r}, name={self.name!r})"

    def clean(self):
        super().clean()
        if self.scope_id:
            validate_reference_value(
                self.scope, field_code=FIELD_CODE_EVENT_TYPE_SCOPE, client_id=self.client_id
            )
        if self.category_id:
            validate_reference_value(
                self.category, field_code=FIELD_CODE_EVENT_TYPE_CATEGORY, client_id=self.client_id
            )


class NeyoCalendarEvent(models.Model):
    """
    Architecture doc §7.4.

    `is_all_day`/`conferencing_url` — ARCH_059. `subject_title`/`subject_subtitle`/
    `subject_image_url`/`subject_highlights`/`subject_actions` — ARCH_060, mirrored
    from NeyoBookingRequest at confirmation (bookings app, not built yet); also
    independently settable for events with no booking origin, which is exactly
    what every row in Neyora-FrontEnd/src/api/mockData.js's mockEvents does today
    (events 71–74 ship those fields blank/empty, event 70 populated) — confirms the
    FE already expects them to be optional/blank, matching `blank=True` below.
    """

    id = models.BigAutoField(primary_key=True)
    calendar = models.ForeignKey(NeyoCalendar, on_delete=models.CASCADE, related_name="events")
    event_type = models.ForeignKey(NeyoEventType, on_delete=models.PROTECT, related_name="events")

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    timezone = models.CharField(max_length=64)

    status = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendar_events_by_status",
        limit_choices_to={"field_code": FIELD_CODE_CALENDAR_EVENT_STATUS},
    )
    visibility = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendar_events_by_visibility",
        limit_choices_to={"field_code": FIELD_CODE_CALENDAR_EVENT_VISIBILITY},
    )
    persona_context = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="calendar_events_by_persona_context",
        limit_choices_to={"field_code": FIELD_CODE_PERSONA_CONTEXT},
        null=True,
        blank=True,
    )

    created_by = models.CharField(max_length=128)
    updated_by = models.CharField(max_length=128, null=True, blank=True)

    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    is_all_day = models.BooleanField(default=False)
    conferencing_url = models.CharField(max_length=500, blank=True)

    subject_title = models.CharField(max_length=255, blank=True)
    subject_subtitle = models.CharField(max_length=255, blank=True)
    subject_image_url = models.CharField(max_length=500, blank=True)
    subject_highlights = models.JSONField(default=list, blank=True)
    subject_actions = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="chk_calendarevent_end_after_start",
            )
        ]
        indexes = [
            models.Index(fields=["calendar", "start_at"]),
        ]

    def __str__(self):
        return f"NeyoCalendarEvent(id={self.id}, title={self.title!r})"

    def clean(self):
        super().clean()
        if self.end_at and self.start_at and self.end_at <= self.start_at:
            raise ValidationError("end_at must be after start_at.")
        client_id = self.calendar.client_id if self.calendar_id else None
        if client_id:
            if self.status_id:
                validate_reference_value(
                    self.status, field_code=FIELD_CODE_CALENDAR_EVENT_STATUS, client_id=client_id
                )
            if self.visibility_id:
                validate_reference_value(
                    self.visibility, field_code=FIELD_CODE_CALENDAR_EVENT_VISIBILITY, client_id=client_id
                )
            if self.persona_context_id:
                validate_reference_value(
                    self.persona_context, field_code=FIELD_CODE_PERSONA_CONTEXT, client_id=client_id
                )


class NeyoEventParticipant(models.Model):
    """
    Architecture doc §7.5. Participation never grants calendar-wide access.

    Not yet wired to any FE file — Neyora-FrontEnd/src/Events/EventDetailPanel.jsx's
    Accept/Decline buttons are still hardcoded; this model is what they'll update
    (`response_status`) once that wiring happens, per §12's invitation flow.
    """

    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(NeyoCalendarEvent, on_delete=models.CASCADE, related_name="participants")
    external_user_id = models.CharField(max_length=128)

    role = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="event_participants_by_role",
        limit_choices_to={"field_code": FIELD_CODE_EVENT_PARTICIPANT_ROLE},
    )
    response_status = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="event_participants_by_response_status",
        limit_choices_to={"field_code": FIELD_CODE_EVENT_PARTICIPANT_RESPONSE_STATUS},
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "external_user_id", "role"],
                name="uniq_eventparticipant_event_user_role",
            )
        ]

    def __str__(self):
        return f"NeyoEventParticipant(event_id={self.event_id}, user={self.external_user_id})"

    def clean(self):
        super().clean()
        client_id = self.event.calendar.client_id if self.event_id else None
        if client_id:
            if self.role_id:
                validate_reference_value(
                    self.role, field_code=FIELD_CODE_EVENT_PARTICIPANT_ROLE, client_id=client_id
                )
            if self.response_status_id:
                validate_reference_value(
                    self.response_status,
                    field_code=FIELD_CODE_EVENT_PARTICIPANT_RESPONSE_STATUS,
                    client_id=client_id,
                )
