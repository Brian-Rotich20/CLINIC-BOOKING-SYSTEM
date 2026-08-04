from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    if isinstance(exc, BookingError):
        return Response({"detail": exc.message}, status=exc.status_code)
    return drf_exception_handler(exc, context)
    
class BookingError(Exception):
    """Base class for all booking-related errors. Carries an HTTP status code
    so the view layer can translate it directly without re-deciding logic."""
    status_code = 400

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class InvalidSlotError(BookingError):
    """Slot falls outside working hours, is in the past, or misaligned to 30-min grid."""
    status_code = 400


class SlotUnavailableError(BookingError):
    """Slot is already booked by someone else."""
    status_code = 409


class AppointmentNotFoundError(BookingError):
    status_code = 404


class AlreadyCancelledError(BookingError):
    status_code = 400