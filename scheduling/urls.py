from django.urls import path

from scheduling.views import BookCalendarSlotView, CalendarEventsView, EnsurePersonalCalendarView

urlpatterns = [
    path("personal/ensure/", EnsurePersonalCalendarView.as_view(), name="calendar-personal-ensure"),
    path("book-slot/", BookCalendarSlotView.as_view(), name="calendar-book-slot"),
    path("<int:calendar_id>/events/", CalendarEventsView.as_view(), name="calendar-events"),
]
