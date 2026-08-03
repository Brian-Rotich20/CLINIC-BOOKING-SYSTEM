from datetime import timedelta, time

from django.test import TestCase
from django.utils import timezone

from apps.doctors.models import Doctor, WorkingHours
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.appointments import services
from apps.appointments.exceptions import (
    AlreadyCancelledError,
    AppointmentNotFoundError,
    InvalidSlotError,
    SlotUnavailableError,
)


class CancelAppointmentTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name="Dr. Achieng")
        self.patient = Patient.objects.create(name="Brian", email="brian@example.com")

        self.target_date = (timezone.now() + timedelta(days=7)).date()
        WorkingHours.objects.create(
            doctor=self.doctor,
            weekday=self.target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        self.start = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(10, 0))
        )
        self.appointment = services.book_appointment(self.doctor, self.patient, self.start)

    def test_successful_cancel(self):
        cancelled = services.cancel_appointment(self.appointment.id, "patient request")
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(cancelled.cancellation_reason, "patient request")

    def test_cancel_frees_the_slot(self):
        services.cancel_appointment(self.appointment.id, "patient request")
        # booking the same slot again should now succeed
        rebooked = services.book_appointment(self.doctor, self.patient, self.start)
        self.assertEqual(rebooked.status, "booked")

    def test_cancel_already_cancelled_raises(self):
        services.cancel_appointment(self.appointment.id, "patient request")
        with self.assertRaises(AlreadyCancelledError):
            services.cancel_appointment(self.appointment.id, "patient request again")

    def test_cancel_requires_reason(self):
        with self.assertRaises(InvalidSlotError):
            services.cancel_appointment(self.appointment.id, "")

    def test_cancel_nonexistent_appointment_raises(self):
        with self.assertRaises(AppointmentNotFoundError):
            services.cancel_appointment(999999, "patient request")


class RescheduleAppointmentTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name="Dr. Achieng")
        self.patient = Patient.objects.create(name="Brian", email="brian@example.com")

        self.target_date = (timezone.now() + timedelta(days=7)).date()
        WorkingHours.objects.create(
            doctor=self.doctor,
            weekday=self.target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        self.original_start = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(10, 0))
        )
        self.new_start = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(11, 0))
        )
        self.appointment = services.book_appointment(
            self.doctor, self.patient, self.original_start
        )

    def test_successful_reschedule(self):
        rescheduled = services.reschedule_appointment(self.appointment.id, self.new_start)
        self.assertEqual(rescheduled.start_time, self.new_start)

    def test_reschedule_frees_original_slot(self):
        services.reschedule_appointment(self.appointment.id, self.new_start)
        # original slot should be bookable again by someone else
        other_patient = Patient.objects.create(name="Amina", email="amina@example.com")
        rebooked = services.book_appointment(self.doctor, other_patient, self.original_start)
        self.assertEqual(rebooked.status, "booked")

    def test_reschedule_to_already_taken_slot_raises(self):
        other_patient = Patient.objects.create(name="Amina", email="amina@example.com")
        services.book_appointment(self.doctor, other_patient, self.new_start)

        with self.assertRaises(SlotUnavailableError):
            services.reschedule_appointment(self.appointment.id, self.new_start)

    def test_reschedule_cancelled_appointment_raises(self):
        services.cancel_appointment(self.appointment.id, "no longer needed")
        with self.assertRaises(InvalidSlotError):
            services.reschedule_appointment(self.appointment.id, self.new_start)

    def test_reschedule_validates_new_slot_like_fresh_booking(self):
        outside_hours = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(20, 0))
        )
        with self.assertRaises(InvalidSlotError):
            services.reschedule_appointment(self.appointment.id, outside_hours)

    def test_reschedule_nonexistent_appointment_raises(self):
        with self.assertRaises(AppointmentNotFoundError):
            services.reschedule_appointment(999999, self.new_start)