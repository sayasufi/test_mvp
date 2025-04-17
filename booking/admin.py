from django.contrib import admin

from .models import Room, Booking


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "floor", "capacity")
    search_fields = ("name",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("room", "date", "start_time", "end_time", "user")
    list_filter = ("date", "room")
