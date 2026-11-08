from django.contrib import admin

from core.models import NeyoClient, NeyoReferenceValue


@admin.register(NeyoReferenceValue)
class NeyoReferenceValueAdmin(admin.ModelAdmin):
    list_display = ("id", "client_id", "field_code", "value_code", "is_active")
    list_filter = ("client_id", "field_code", "is_active")
    search_fields = ("field_code", "value_code")


@admin.register(NeyoClient)
class NeyoClientAdmin(admin.ModelAdmin):
    list_display = ("client_id", "name", "status", "plan_tier", "api_key", "created_at")
    search_fields = ("client_id", "name")
    readonly_fields = ("api_key", "created_at")
