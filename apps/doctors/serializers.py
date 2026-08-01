from rest_framework import serializers


class AvailabilityQuerySerializer(serializers.Serializer):
    """Validates the ?date= query param on GET /doctors/{id}/availability."""
    date = serializers.DateField()


class AvailabilitySlotSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()