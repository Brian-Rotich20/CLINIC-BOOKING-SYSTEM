from datetime import date, timedelta, time

from django.test import TestCase
from django.utils import timezone

from apps.doctors.models import Doctor, WorkingHours
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.appointments import services


class GetAvailableSlotsTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name="Dr. Achieng")
        self.patient = Patient.objects.create(name="Brian", email="brian@example.com")

        # Use a weekday far enough in the future to safely be > 1hr lead time
        self.target_date = (timezone.now() + timedelta(days=7)).date()
        weekday = self.target_date.weekday()

        WorkingHours.objects.create(
            doctor=self.doctor,
            weekday=weekday,
            start_time=time(9, 0),
            end_time=time(11, 0),
        )

    def test_returns_all_slots_when_none_booked(self):
        slots = services.get_available_slots(self.doctor, self.target_date)
        # 9:00-11:00 in 30-min increments = 4 slots
        self.assertEqual(len(slots), 4)

    def test_excludes_booked_slot(self):
        booked_start = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(9, 0))
        )
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=booked_start,
            end_time=booked_start + timedelta(minutes=30),
            status=Appointment.Status.BOOKED,
        )

        slots = services.get_available_slots(self.doctor, self.target_date)
        self.assertNotIn(booked_start, slots)
        self.assertEqual(len(slots), 3)

    def test_cancelled_slot_still_available(self):
        booked_start = timezone.make_aware(
            timezone.datetime.combine(self.target_date, time(9, 0))
        )
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=booked_start,
            end_time=booked_start + timedelta(minutes=30),
            status=Appointment.Status.CANCELLED,
            cancellation_reason="changed mind",
        )

        slots = services.get_available_slots(self.doctor, self.target_date)
        self.assertIn(booked_start, slots)

    def test_no_working_hours_returns_empty(self):
        other_date = self.target_date + timedelta(days=1)
        slots = services.get_available_slots(self.doctor, other_date)
        self.assertEqual(slots, [])

    def test_excludes_slots_within_lead_time(self):
        # working hours for "today" starting in 30 minutes — inside the 1hr guard
        today = timezone.now().date()
        near_future = timezone.now() + timedelta(minutes=30)
        WorkingHours.objects.create(
            doctor=self.doctor,
            weekday=today.weekday(),
            start_time=near_future.time(),
            end_time=(near_future + timedelta(hours=2)).time(),
        )
        slots = services.get_available_slots(self.doctor, today)
        self.assertTrue(all(s >= timezone.now() + services.MIN_LEAD_TIME for s in slots))