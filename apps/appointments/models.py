from django.db import models
from django.core.exceptions import ValidationError

from apps.doctors.models import Doctor
from apps.patients.models import Patient


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="appointments"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="appointments"
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()  # always start_time + 30 min, stored for query convenience

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.BOOKED
    )
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            # DB-level guard against double-booking a slot.
            # Only enforced while status='booked' — cancelled appointments
            # free the slot up for others without needing to delete rows.
            models.UniqueConstraint(
                fields=["doctor", "start_time"],
                condition=models.Q(status="booked"),
                name="unique_booked_slot_per_doctor",
            )
        ]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("end_time must be after start_time.")
        if self.status == self.Status.CANCELLED and not self.cancellation_reason:
            raise ValidationError(
                "cancellation_reason is required when status is cancelled."
            )

    def __str__(self):
        return f"{self.patient.name} with {self.doctor.name} @ {self.start_time}"