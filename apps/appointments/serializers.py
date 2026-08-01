from rest_framework import serializers

from apps.appointments.models import Appointment
from apps.doctors.models import Doctor
from apps.patients.models import Patient


class AppointmentSerializer(serializers.ModelSerializer):
    """Output representation — used by all endpoints that return an appointment."""
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "doctor", "doctor_name", "patient", "patient_name",
            "start_time", "end_time", "status", "cancellation_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class BookAppointmentSerializer(serializers.Serializer):
    """Input for POST /appointments. Only structural validation here
    (field types, existence of FKs) — business rules live in services.py."""
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), source="doctor"
    )
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source="patient"
    )
    start_time = serializers.DateTimeField()


class CancelAppointmentSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, allow_blank=False)


class RescheduleAppointmentSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()