from django.urls import path

from core.views import WidgetTokenView

urlpatterns = [
    path("widget-tokens/", WidgetTokenView.as_view(), name="widget-tokens"),
]
