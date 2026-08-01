from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.appointments.serializers import AppointmentSerializer


class PatientUpcomingAppointmentsView(APIView):
    """GET /patients/{id}/appointments — upcoming, non-cancelled, sorted by date."""

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id)

        appointments = Appointment.objects.filter(
            patient=patient,
            status=Appointment.Status.BOOKED,
            start_time__gte=timezone.now(),
        ).order_by("start_time")

        return Response(
            AppointmentSerializer(appointments, many=True).data,
            status=status.HTTP_200_OK,
        )