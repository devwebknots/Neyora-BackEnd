"""
URL configuration for neyora_backend project.

Root API surface. Per §13 of the architecture doc, Neyora's own API is "flat,
unversioned, client-authenticated" — every area (notifications/, conversations/,
calendars/, availability/, booking-requests/, core-reference-values/,
widget-tokens/) gets mounted at /api/<area>/ as its app is built (Phase 1A–1D).
Only /api/health/ is unauthenticated, by design (see healthcheck/views.py).
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", include("healthcheck.urls")),
    path("api/", include("core.urls")),               # /api/widget-tokens/
    path("api/calendars/", include("scheduling.urls")),  # /api/calendars/...
]
