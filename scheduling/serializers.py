from rest_framework import serializers

from scheduling.models import NeyoCalendar, NeyoCalendarEvent


class NeyoCalendarSerializer(serializers.ModelSerializer):
    # Reference-value FKs come back as their value_code string (e.g.
    # "PERSONAL", "ACTIVE") — the same shape Neyora-FrontEnd/src/api/
    # mockData.js's mockCalendars already use, not the internal FK id.
    calendar_type = serializers.SlugRelatedField(slug_field="value_code", read_only=True)
    status = serializers.SlugRelatedField(slug_field="value_code", read_only=True)

    class Meta:
        model = NeyoCalendar
        fields = [
            "id", "client_id", "name", "calendar_type", "external_owner_id",
            "account_id", "property", "timezone", "status", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class NeyoCalendarEventSerializer(serializers.ModelSerializer):
    status = serializers.SlugRelatedField(slug_field="value_code", read_only=True)
    visibility = serializers.SlugRelatedField(slug_field="value_code", read_only=True)
    persona_context = serializers.SlugRelatedField(slug_field="value_code", read_only=True)

    class Meta:
        model = NeyoCalendarEvent
        fields = [
            "id", "calendar", "event_type", "title", "description",
            "start_at", "end_at", "timezone", "status", "visibility",
            "persona_context", "location", "notes", "is_all_day",
            "conferencing_url", "subject_title", "subject_subtitle",
            "subject_image_url", "subject_highlights", "subject_actions",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class NeyoCalendarEventCreateSerializer(serializers.ModelSerializer):
    """
    Write-only input for POST /api/calendars/{id}/events/ (§7.4/§13) — a
    deliberately small v1 surface (title/description/start/end/timezone/
    location/is_all_day/conferencing_url). `event_type`/`status`/`visibility`
    aren't accepted here yet: no client-scoped NeyoEventType reference data
    has been synced (that's the CoreNeyoraFieldMapping/sync work deferred out
    of Step 2 of the integration plan), so the view assigns sensible defaults
    itself (a "GENERAL" event type, SCHEDULED status, SHARED_DETAILS
    visibility) rather than asking the caller to supply FKs that don't exist
    anywhere in the UI yet.
    """

    class Meta:
        model = NeyoCalendarEvent
        fields = [
            "title", "description", "start_at", "end_at", "timezone",
            "location", "is_all_day", "conferencing_url",
        ]


class BookCalendarSlotRequestSerializer(serializers.Serializer):
    """
    Input for POST /api/calendars/book-slot/ (scheduling/views.py's
    BookCalendarSlotView — see its own docstring for the v1 scope this is
    deliberately limited to). A plain Serializer, not a ModelSerializer: the
    host/requester ids aren't NeyoCalendarEvent fields themselves, and
    subject_title/subject_subtitle are display-enrichment per ARCH_060
    rather than core booking data.
    """

    host_external_user_id = serializers.CharField()
    requester_external_user_id = serializers.CharField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    timezone = serializers.CharField(required=False, default="UTC")
    subject_title = serializers.CharField(required=False, allow_blank=True, default="")
    subject_subtitle = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
