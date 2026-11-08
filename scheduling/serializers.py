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
