from django.contrib import admin

from scheduling.models import (
    NeyoCalendar,
    NeyoCalendarEvent,
    NeyoCalendarMembership,
    NeyoEventParticipant,
    NeyoEventType,
)


@admin.register(NeyoCalendar)
class NeyoCalendarAdmin(admin.ModelAdmin):
    list_display = ("id", "client_id", "name", "calendar_type", "external_owner_id", "account_id", "status")
    list_filter = ("client_id", "calendar_type", "status")
    search_fields = ("name", "external_owner_id", "account_id")


@admin.register(NeyoCalendarMembership)
class NeyoCalendarMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "calendar", "external_user_id", "access_level", "status")
    list_filter = ("access_level", "status")


@admin.register(NeyoEventType)
class NeyoEventTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "client_id", "name", "code", "scope", "category", "is_active")
    list_filter = ("client_id", "scope", "category", "is_active")
    search_fields = ("name", "code")


@admin.register(NeyoCalendarEvent)
class NeyoCalendarEventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "calendar", "event_type", "start_at", "end_at", "status", "visibility")
    list_filter = ("status", "visibility", "is_all_day")
    search_fields = ("title", "location")


@admin.register(NeyoEventParticipant)
class NeyoEventParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "external_user_id", "role", "response_status")
    list_filter = ("role", "response_status")
