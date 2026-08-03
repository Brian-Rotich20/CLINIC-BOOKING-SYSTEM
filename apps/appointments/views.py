from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.appointments import services
from apps.appointments.serializers import (
    AppointmentSerializer,
    BookAppointmentSerializer,
    CancelAppointmentSerializer,
    RescheduleAppointmentSerializer,
)


@extend_schema(
    request=BookAppointmentSerializer,
    responses={201: AppointmentSerializer},
    summary="Book an appointment",
    description=(
        "Books a 30-minute slot for a patient with a doctor. Validates that "
        "the slot falls within the doctor's working hours, is not in the "
        "past, is at least 1 hour from now, and is not already taken."
    ),
    examples=[
        OpenApiExample(
            "Book request",
            value={"doctor_id": 1, "patient_id": 1, "start_time": "2026-08-10T10:00:00Z"},
            request_only=True,
        ),
    ],
)
class AppointmentCreateView(APIView):
    """POST /appointments"""

    def post(self, request):
        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = services.book_appointment(
            doctor=serializer.validated_data["doctor"],
            patient=serializer.validated_data["patient"],
            start_time=serializer.validated_data["start_time"],
        )
        return Response(
            AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED
        )


@extend_schema(
    request=CancelAppointmentSerializer,
    responses={200: AppointmentSerializer},
    summary="Cancel an appointment",
    description=(
        "Cancels a booked appointment with a required reason. Returns an "
        "error if the appointment is already cancelled. The slot becomes "
        "available for others once cancelled."
    ),
    examples=[
        OpenApiExample(
            "Cancel request",
            value={"reason": "patient requested cancellation"},
            request_only=True,
        ),
    ],
)
class AppointmentCancelView(APIView):
    """PATCH /appointments/{id}/cancel"""

    def patch(self, request, appointment_id):
        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = services.cancel_appointment(
            appointment_id=appointment_id,
            reason=serializer.validated_data["reason"],
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)


@extend_schema(
    request=RescheduleAppointmentSerializer,
    responses={200: AppointmentSerializer},
    summary="Reschedule an appointment",
    description=(
        "Moves a booked appointment to a new slot. The original slot "
        "becomes available again, and the new slot is validated exactly "
        "as a fresh booking would be. Returns an error if the appointment "
        "is already cancelled."
    ),
    examples=[
        OpenApiExample(
            "Reschedule request",
            value={"start_time": "2026-08-10T11:00:00Z"},
            request_only=True,
        ),
    ],
)
class AppointmentRescheduleView(APIView):
    """PATCH /appointments/{id}/reschedule"""

    def patch(self, request, appointment_id):
        serializer = RescheduleAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = services.reschedule_appointment(
            appointment_id=appointment_id,
            new_start_time=serializer.validated_data["start_time"],
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)