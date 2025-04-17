import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from booking.models import Room, Booking


# ---------------------------
# Фикстуры и фабрики
# ---------------------------
@pytest.fixture
def api_client():
    client = APIClient()
    client.defaults['HTTP_HOST'] = 'testserver'
    return client


@pytest.fixture
def create_user(db):
    def _create_user(**kwargs):
        return User.objects.create_user(**kwargs)

    return _create_user


@pytest.fixture
def create_admin(db):
    def _create_admin(**kwargs):
        return User.objects.create_superuser(**kwargs)

    return _create_admin


@pytest.fixture
def user(create_user):
    return create_user(username='user', password='user123', email='user@example.com')


@pytest.fixture
def admin(create_admin):
    return create_admin(username='admin', password='admin123', email='admin@example.com')


@pytest.fixture
def room(db):
    return Room.objects.create(name="Main Room", capacity=10, floor=1)


@pytest.fixture
def auth_client(api_client, user):
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin):
    refresh = RefreshToken.for_user(admin)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return api_client


# ---------------------------
# Тесты регистрации
# ---------------------------
@pytest.mark.django_db
class TestRegistration:
    def test_successful_registration(self, api_client):
        url = reverse('register')
        data = {"username": "newuser", "email": "newuser@example.com", "password": "newpass123"}
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        created_user = User.objects.get(username="newuser")
        assert created_user.email == "newuser@example.com"

    def test_registration_missing_fields(self, api_client):
        url = reverse('register')
        data = {"username": "incomplete"}
        response = api_client.post(url, data, format='json')
        assert response.status_code == 400


# ---------------------------
# Тесты комнат (Room endpoints)
# ---------------------------
@pytest.mark.django_db
class TestRoomEndpoints:
    def test_room_list_as_user(self, auth_client, room):
        url = reverse('room-list')
        response = auth_client.get(url)
        assert response.status_code == 200
        # С пагинацией данные находятся по ключу "results"
        results = response.data.get("results", response.data)
        assert any(r['id'] == room.id for r in results)

    def test_room_create_non_admin(self, auth_client):
        url = reverse('room-list')
        data = {"name": "Room 2", "capacity": 15, "floor": 2}
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 403

    def test_room_create_as_admin(self, admin_client):
        url = reverse('room-list')
        data = {"name": "Room 3", "capacity": 20, "floor": 3}
        response = admin_client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['name'] == "Room 3"

    def test_room_update_and_delete(self, admin_client, room):
        # Update room
        url = reverse('room-detail', args=[room.id])
        update_data = {"name": "Updated Room", "capacity": 12, "floor": room.floor}
        response = admin_client.patch(url, update_data, format='json')
        assert response.status_code == 200
        room.refresh_from_db()
        assert room.name == "Updated Room"
        # Delete room
        response = admin_client.delete(url)
        assert response.status_code == 204
        with pytest.raises(Room.DoesNotExist):
            Room.objects.get(id=room.id)

    def test_free_rooms_filter(self, auth_client, room, user):
        # Создаем бронирование, чтобы комната была занята
        Booking.objects.create(
            user=user,
            room=room,
            date=datetime.date(2025, 5, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0)
        )
        url = reverse('room-free-rooms')
        params = {"date": "2025-05-01", "start_time": "10:30:00", "end_time": "11:30:00"}
        response = auth_client.get(url, params)
        assert response.status_code == 200
        # Ответ оформлен через пагинацию
        results = response.data.get("results", response.data)
        assert len(results) == 0


# ---------------------------
# Тесты бронирований (Booking endpoints)
# ---------------------------
@pytest.mark.django_db
class TestBookingEndpoints:
    def test_create_booking(self, auth_client, room, user):
        url = reverse('booking-list')
        data = {"room": room.id, "date": "2025-05-01", "start_time": "10:00:00", "end_time": "11:00:00"}
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 201
        booking = Booking.objects.first()
        assert booking.user == user

    def test_booking_conflict(self, auth_client, room, user):
        Booking.objects.create(
            user=user,
            room=room,
            date=datetime.date(2025, 5, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0)
        )
        url = reverse('booking-list')
        data = {"room": room.id, "date": "2025-05-01", "start_time": "10:30:00", "end_time": "11:30:00"}
        response = auth_client.post(url, data, format='json')
        assert response.status_code == 400

    def test_update_and_delete_booking(self, auth_client, room, user):
        booking = Booking.objects.create(
            user=user,
            room=room,
            date=datetime.date(2025, 5, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0)
        )
        url = reverse('booking-detail', args=[booking.id])
        update_data = {"start_time": "10:15:00", "end_time": "11:15:00"}
        response = auth_client.patch(url, update_data, format='json')
        assert response.status_code == 200
        booking.refresh_from_db()
        assert booking.start_time.strftime("%H:%M:%S") == "10:15:00"
        response = auth_client.delete(url)
        assert response.status_code == 204
        with pytest.raises(Booking.DoesNotExist):
            Booking.objects.get(id=booking.id)

    def test_user_bookings_visibility(self, api_client, create_user, room, user):
        # Создаем бронирование другого пользователя
        other_user = create_user(username='other', password='other123', email='other@example.com')
        Booking.objects.create(
            user=other_user,
            room=room,
            date=datetime.date(2025, 5, 2),
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0)
        )
        # Создаем бронирование текущего пользователя
        Booking.objects.create(
            user=user,
            room=room,
            date=datetime.date(2025, 5, 2),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(12, 0)
        )
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        url = reverse('booking-list')
        response = api_client.get(url)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]['user'] == user.id

    def test_admin_sees_all_bookings(self, admin_client, room, admin):
        Booking.objects.create(
            user=admin,
            room=room,
            date=datetime.date(2025, 5, 3),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0)
        )
        Booking.objects.create(
            user=admin,
            room=room,
            date=datetime.date(2025, 5, 3),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(12, 0)
        )
        url = reverse('booking-list')
        response = admin_client.get(url)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) == 2

    def test_booking_partial_update_invalid(self, auth_client, room, user):
        """
        Тест, проверяющий, что при частичном обновлении (без передачи поля room)
        данные подставляются из текущего экземпляра, а затем валидация проходит корректно.
        """
        booking = Booking.objects.create(
            user=user,
            room=room,
            date=datetime.date(2025, 5, 4),
            start_time=datetime.time(14, 0),
            end_time=datetime.time(15, 0)
        )
        url = reverse('booking-detail', args=[booking.id])
        update_data = {"start_time": "14:15:00"}  # end_time не передаем => подставится текущее значение
        response = auth_client.patch(url, update_data, format='json')
        assert response.status_code == 200
        booking.refresh_from_db()
        # Проверяем, что start_time обновился, а end_time осталось прежним
        assert booking.start_time.strftime("%H:%M:%S") == "14:15:00"
        assert booking.end_time.strftime("%H:%M:%S") == "15:00:00"


@pytest.mark.django_db
def test_unauthenticated_access(api_client):
    """
    Нeаутентифицированный пользователь не может получить доступ к защищённым эндпоинтам.
    """
    url = reverse('booking-list')
    response = api_client.get(url)
    assert response.status_code in (401, 400)

    url = reverse('room-list')
    response = api_client.get(url)
    assert response.status_code in (401, 400)
