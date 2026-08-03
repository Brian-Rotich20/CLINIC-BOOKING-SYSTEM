from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.doctors.models import Doctor
from apps.doctors.serializers import AvailabilityQuerySerializer, AvailabilitySlotSerializer
from apps.appointments import services


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Date to check availability for, format YYYY-MM-DD.",
        ),
    ],
    responses={200: AvailabilitySlotSerializer(many=True)},
    summary="Get a doctor's available slots for a given date",
    description=(
        "Returns all available 30-minute slots for a doctor on a given date, "
        "derived from their working hours minus already-booked appointments. "
        "Excludes slots within 1 hour of the current time."
    ),
)
class DoctorAvailabilityView(APIView):
    """GET /doctors/{id}/availability?date=YYYY-MM-DD"""

    def get(self, request, doctor_id):
        doctor = get_object_or_404(Doctor, id=doctor_id)

        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        slots = services.get_available_slots(doctor, query.validated_data["date"])
        data = AvailabilitySlotSerializer(
            [{"start_time": s} for s in slots], many=True
        ).data
        return Response(data, status=status.HTTP_200_OK)