from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RoomViewSet, BookingViewSet, RegistrationView

router = DefaultRouter()
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("auth/register/", RegistrationView.as_view(), name="register"),
    path("", include(router.urls)),
]
