from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Room, Booking
from .pagination import CustomCursorPagination
from .serializers import RoomSerializer, BookingSerializer, RegistrationSerializer


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]
    queryset = []


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['floor', 'capacity']

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        # Всегда читаем список комнат из мастера
        return Room.objects.using('default').all()

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, description="Дата (YYYY-MM-DD)", type=openapi.TYPE_STRING,
                              required=True),
            openapi.Parameter('start_time', openapi.IN_QUERY, description="Время начала (HH:MM:SS)",
                              type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('end_time', openapi.IN_QUERY, description="Время окончания (HH:MM:SS)",
                              type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('floor', openapi.IN_QUERY, description="Этаж (опционально)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('capacity', openapi.IN_QUERY, description="Минимальная вместимость (опционально)",
                              type=openapi.TYPE_INTEGER),
        ],
        operation_description="Возвращает список свободных комнат по заданным параметрам: date, start_time, end_time, floor, capacity"
    )
    @action(detail=False, methods=['get'], url_path='free')
    def free_rooms(self, request):
        date = request.query_params.get('date')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        if not (date and start_time and end_time):
            return Response(
                {"detail": "Параметры 'date', 'start_time' и 'end_time' обязательны."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filters = {}
        floor = request.query_params.get('floor')
        capacity = request.query_params.get('capacity')
        if floor:
            filters['floor'] = floor
        if capacity:
            filters['capacity__gte'] = capacity

        # Всегда работаем с мастер‑БД при определении свободных комнат
        rooms = Room.objects.using('default').filter(**filters)
        busy_room_ids = Booking.objects.using('default').filter(
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).values_list('room_id', flat=True)
        free_rooms = rooms.exclude(id__in=busy_room_ids)

        page = self.paginate_queryset(free_rooms)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(free_rooms, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    pagination_class = CustomCursorPagination
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date', 'room']
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Booking.objects.none()
        if self.request.user.is_staff:
            return Booking.objects.all().select_related('room', 'user')
        return Booking.objects.filter(user=self.request.user).select_related('room')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Создание бронирования",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['room', 'date', 'start_time', 'end_time'],
            properties={
                'room': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID комнаты"),
                'date': openapi.Schema(type=openapi.TYPE_STRING, description="Дата бронирования (YYYY-MM-DD)"),
                'start_time': openapi.Schema(type=openapi.TYPE_STRING, description="Время начала (HH:MM:SS)"),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, description="Время окончания (HH:MM:SS)"),
            }
        ),
        responses={201: BookingSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
