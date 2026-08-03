from django.urls import path

from apps.appointments.views import (
    AppointmentCreateView,
    AppointmentCancelView,
    AppointmentRescheduleView,
)

urlpatterns = [
    path("", AppointmentCreateView.as_view(), name="appointment-create"),
    path("<int:appointment_id>/cancel", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("<int:appointment_id>/reschedule", AppointmentRescheduleView.as_view(), name="appointment-reschedule"),
]