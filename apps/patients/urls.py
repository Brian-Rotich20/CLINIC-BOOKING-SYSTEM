from django.urls import path

from apps.patients.views import PatientUpcomingAppointmentsView

urlpatterns = [
    path("patients/<int:patient_id>/appointments", PatientUpcomingAppointmentsView.as_view(), name="patient-appointments"),
]