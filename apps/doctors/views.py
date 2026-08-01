from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.doctors.models import Doctor
from apps.doctors.serializers import AvailabilityQuerySerializer, AvailabilitySlotSerializer
from apps.appointments import services


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