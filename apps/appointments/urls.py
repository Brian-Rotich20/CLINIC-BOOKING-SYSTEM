from django.urls import path

from apps.appointments.views import (
    AppointmentCreateView,
    AppointmentCancelView,
    AppointmentRescheduleView,
)

urlpatterns = [
    path("appointments", AppointmentCreateView.as_view(), name="appointment-create"),
    path("appointments/<int:appointment_id>/cancel", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("appointments/<int:appointment_id>/reschedule", AppointmentRescheduleView.as_view(), name="appointment-reschedule"),
]