"""
Business logic for the clinic booking system.

Kept out of views.py deliberately: this is the logic Section 2's constraints
care about most ("validate working hours / not in past / not taken") and it
needs to be unit-testable without spinning up the HTTP layer.
"""
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.doctors.models import Doctor, WorkingHours
from apps.appointments.models import Appointment
from apps.appointments.exceptions import (
    InvalidSlotError,
    SlotUnavailableError,
    AppointmentNotFoundError,
    AlreadyCancelledError,
)

SLOT_MINUTES = 30
MIN_LEAD_TIME = timedelta(hours=1)  # bonus: no bookings within 1hr of now


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def get_available_slots(doctor: Doctor, date):
    """Return a list of available slot start datetimes (tz-aware) for a
    doctor on a given date, derived from working hours minus booked slots."""
    weekday = date.weekday()  # Monday=0 ... Sunday=6, matches WorkingHours.Weekday

    hours_today = WorkingHours.objects.filter(doctor=doctor, weekday=weekday)
    if not hours_today.exists():
        return []

    booked_starts = set(
        Appointment.objects.filter(
            doctor=doctor,
            status=Appointment.Status.BOOKED,
            start_time__date=date,
        ).values_list("start_time", flat=True)
    )

    slots = []
    for window in hours_today:
        current = timezone.make_aware(datetime.combine(date, window.start_time))
        end = timezone.make_aware(datetime.combine(date, window.end_time))

        while current + timedelta(minutes=SLOT_MINUTES) <= end:
            if current not in booked_starts and current >= timezone.now() + MIN_LEAD_TIME:
                slots.append(current)
            current += timedelta(minutes=SLOT_MINUTES)

    return sorted(slots)


# ---------------------------------------------------------------------------
# Validation shared by booking + reschedule
# ---------------------------------------------------------------------------

def _validate_slot(doctor: Doctor, start_time):
    """Raises InvalidSlotError if the slot fails any pre-condition.
    Does NOT check for conflicts — that's enforced by the DB constraint
    inside the atomic block in book_appointment/reschedule_appointment."""
    now = timezone.now()

    if start_time < now:
        raise InvalidSlotError("Cannot book a slot in the past.")

    if start_time < now + MIN_LEAD_TIME:
        raise InvalidSlotError("Bookings must be made at least 1 hour in advance.")

    if start_time.minute % SLOT_MINUTES != 0 or start_time.second != 0:
        raise InvalidSlotError("Appointments must start on a 30-minute boundary.")

    weekday = start_time.weekday()
    slot_time = start_time.time()
    within_hours = WorkingHours.objects.filter(
        doctor=doctor,
        weekday=weekday,
        start_time__lte=slot_time,
        end_time__gt=slot_time,
    ).exists()

    if not within_hours:
        raise InvalidSlotError("Selected time is outside the doctor's working hours.")


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------

def book_appointment(doctor: Doctor, patient, start_time):
    _validate_slot(doctor, start_time)
    end_time = start_time + timedelta(minutes=SLOT_MINUTES)

    try:
        with transaction.atomic():
            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                start_time=start_time,
                end_time=end_time,
                status=Appointment.Status.BOOKED,
            )
    except IntegrityError:
        # unique_booked_slot_per_doctor constraint tripped — someone else
        # booked this exact slot in the gap between the check and the insert.
        raise SlotUnavailableError("This slot was just booked by someone else.")

    return appointment


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def cancel_appointment(appointment_id, reason: str):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        raise AppointmentNotFoundError("Appointment not found.")

    if appointment.status == Appointment.Status.CANCELLED:
        raise AlreadyCancelledError("Appointment is already cancelled.")

    if not reason:
        raise InvalidSlotError("A cancellation reason is required.")

    appointment.status = Appointment.Status.CANCELLED
    appointment.cancellation_reason = reason
    appointment.save(update_fields=["status", "cancellation_reason", "updated_at"])
    return appointment


# ---------------------------------------------------------------------------
# Reschedule
# ---------------------------------------------------------------------------

def reschedule_appointment(appointment_id, new_start_time):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        raise AppointmentNotFoundError("Appointment not found.")

    if appointment.status == Appointment.Status.CANCELLED:
        raise InvalidSlotError("Cannot reschedule a cancelled appointment.")

    _validate_slot(appointment.doctor, new_start_time)
    new_end_time = new_start_time + timedelta(minutes=SLOT_MINUTES)

    try:
        with transaction.atomic():
            # Free the old slot and claim the new one in one transaction so
            # the doctor is never briefly double-booked or slot-less.
            appointment.start_time = new_start_time
            appointment.end_time = new_end_time
            appointment.save(update_fields=["start_time", "end_time", "updated_at"])
    except IntegrityError:
        raise SlotUnavailableError("The new slot was just booked by someone else.")

    return appointment