from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.appointments import services
from apps.appointments.serializers import (
    AppointmentSerializer,
    BookAppointmentSerializer,
    CancelAppointmentSerializer,
    RescheduleAppointmentSerializer,
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