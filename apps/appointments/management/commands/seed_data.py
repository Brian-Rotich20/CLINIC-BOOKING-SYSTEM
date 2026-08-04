"""
python manage.py seed_data

Creates a small, fixed set of sample data so anyone with the live URL can
immediately test every endpoint without needing admin credentials. Safe to
run on every deploy — uses get_or_create, so it never duplicates data.
"""
from datetime import time

from django.core.management.base import BaseCommand

from apps.doctors.models import Doctor, WorkingHours
from apps.patients.models import Patient


class Command(BaseCommand):
    help = "Seed the database with sample doctors, working hours, and a patient for API testing."

    def handle(self, *args, **options):
        doctor, created = Doctor.objects.get_or_create(
            name="Dr. Jane Achieng",
            defaults={"specialty": "General Practice"},
        )
        self.stdout.write(
            self.style.SUCCESS(f"Doctor id={doctor.id} {'created' if created else 'already exists'}")
        )

        # Mon–Fri, 09:00–17:00
        for weekday in range(0, 5):
            WorkingHours.objects.get_or_create(
                doctor=doctor,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        self.stdout.write(self.style.SUCCESS("Working hours set: Mon-Fri 09:00-17:00"))

        patient, created = Patient.objects.get_or_create(
            email="test.patient@example.com",
            defaults={"name": "Test Patient", "phone": "0700000000"},
        )
        self.stdout.write(
            self.style.SUCCESS(f"Patient id={patient.id} {'created' if created else 'already exists'}")
        )

        self.stdout.write(self.style.SUCCESS(
            f"\nReady to test:\n"
            f"  GET  /doctors/{doctor.id}/availability?date=<any upcoming weekday, YYYY-MM-DD>\n"
            f"  POST /appointments  {{\"doctor_id\": {doctor.id}, \"patient_id\": {patient.id}, \"start_time\": \"...\"}}"
        ))