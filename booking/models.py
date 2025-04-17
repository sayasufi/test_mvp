from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from psqlextra.models import PostgresPartitionedModel
from psqlextra.types import PostgresPartitioningMethod


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField()
    floor = models.IntegerField()

    def __str__(self):
        return f"{self.name} (Floor {self.floor}, capacity {self.capacity})"

    class Meta:
        ordering = ["floor", "name"]


class Booking(PostgresPartitionedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings"
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class PartitioningMeta:
        method = PostgresPartitioningMethod.RANGE
        key = ["date"]

    def clean(self):
        # 1) Проверка корректности временного интервала
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # 2) Конфликт по комнате в это же время
        room_conflicts = (
            Booking.objects.filter(
                room=self.room,
                date=self.date,
            )
            .exclude(pk=self.pk)
            .filter(
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
        )
        if room_conflicts.exists():
            raise ValidationError(
                "This booking conflicts with an existing booking in this room."
            )

        # 3) Конфликт по пользователю: чтобы у одного юзера не было пересекающихся броней в разных комнатах
        user_conflicts = (
            Booking.objects.filter(
                user=self.user,
                date=self.date,
            )
            .exclude(pk=self.pk)
            .filter(
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
        )
        if user_conflicts.exists():
            raise ValidationError(
                "You already have another booking at this time in a different room."
            )

    def __str__(self):
        return f"{self.room.name} – {self.date}: {self.start_time} - {self.end_time}"

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = ("room", "date", "start_time", "end_time")
        indexes = [
            # поиск по комнате+дате+времени
            models.Index(
                fields=["room", "date", "start_time", "end_time"],
                name="idx_room_date_time",
            ),
            # поиск пересечений по пользователю
            models.Index(
                fields=["user", "date", "start_time", "end_time"],
                name="idx_user_date_time",
            ),
            # составной индекс для быстрого поиска свободных комнат
            models.Index(
                fields=["date", "start_time", "end_time", "room"],
                name="idx_date_start_end_room",
            ),
        ]
