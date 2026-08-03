from datetime import timedelta, time

from django.test import TestCase
from django.utils import timezone

from apps.doctors.models import Doctor, WorkingHours
from apps.patients.models import Patient
from apps.appointments import services
from apps.appointments.exceptions import InvalidSlotError, SlotUnavailableError


class BookAppointmentTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name="Dr. Achieng")
        self.patient = Patient.objects.create(name="Brian", email="brian@example.com")

        self.target_date = (timezone.now() + timedelta(days=7)).date()
        self.weekday = self.target_date.weekday()

        WorkingHours.objects.create(
            doctor=self.doctor,
            weekday=self.weekday,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        self.valid_start = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(10, 0))
        )

    def test_successful_booking(self):
        appointment = services.book_appointment(self.doctor, self.patient, self.valid_start)
        self.assertEqual(appointment.status, "booked")
        self.assertEqual(appointment.end_time, self.valid_start + timedelta(minutes=30))

    def test_rejects_double_booking_same_slot(self):
        services.book_appointment(self.doctor, self.patient, self.valid_start)
        with self.assertRaises(SlotUnavailableError):
            services.book_appointment(self.doctor, self.patient, self.valid_start)

    def test_rejects_slot_in_the_past(self):
        past = timezone.now() - timedelta(days=1)
        with self.assertRaises(InvalidSlotError):
            services.book_appointment(self.doctor, self.patient, past)

    def test_rejects_slot_within_one_hour_lead_time(self):
        too_soon = timezone.now() + timedelta(minutes=30)
        with self.assertRaises(InvalidSlotError):
            services.book_appointment(self.doctor, self.patient, too_soon)

    def test_rejects_slot_outside_working_hours(self):
        outside_hours = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(18, 0))
        )
        with self.assertRaises(InvalidSlotError):
            services.book_appointment(self.doctor, self.patient, outside_hours)

    def test_rejects_slot_not_on_30_minute_boundary(self):
        misaligned = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(10, 15))
        )
        with self.assertRaises(InvalidSlotError):
            services.book_appointment(self.doctor, self.patient, misaligned)

    def test_rejects_slot_on_day_with_no_working_hours(self):
        other_date = self.target_date + timedelta(days=1)
        no_hours_slot = timezone.make_aware(
            timezone.datetime.combine(other_date, time(10, 0))
        )
        with self.assertRaises(InvalidSlotError):
            services.book_appointment(self.doctor, self.patient, no_hours_slot)