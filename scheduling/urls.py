from django.urls import path

from scheduling.views import CalendarEventsView, EnsurePersonalCalendarView

urlpatterns = [
    path("personal/ensure/", EnsurePersonalCalendarView.as_view(), name="calendar-personal-ensure"),
    path("<int:calendar_id>/events/", CalendarEventsView.as_view(), name="calendar-events"),
]
