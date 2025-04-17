#!/usr/bin/env python3
"""
Скрипт интеграционного тестирования и простого нагрузочного тестирования для Booking API.

Запуск (контейнеры должны быть запущены):
    export BASE_URL=http://localhost:8000/api
    export DATABASE_URL=postgres://booking:booking@localhost:5432/booking
    python integration_test.py
"""
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import psycopg2
import requests

# Настройки
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000/api')
DB_URL = os.getenv('DATABASE_URL', 'postgres://booking:booking@localhost:5432/booking')

# Учётные данные для тестов
ADMIN_CRED = {'username': 'admin_integ', 'password': 'AdminPass123', 'email': 'admin@example.com'}
USER_CRED = {'username': 'user_integ', 'password': 'UserPass123', 'email': 'user@example.com'}

# HTTP-сессия
session = requests.Session()
results = []


def log(step, ok, info):
    mark = '✅' if ok else '❌'
    print(f"{mark} {step}: {info or '<нет данных>'}")
    results.append((step, ok, info))


# Регистрация и вход
# Возвращает access token
def register_and_login(creds, role):
    # Регистрация
    r = session.post(f"{BASE_URL}/auth/register/", json=creds)
    if r.status_code == 201:
        log(f"Регистрация {role}", True, "")
    elif r.status_code == 400 and 'username' in r.json():
        log(f"Регистрация {role}", True, "Пользователь уже существует, пропускаем")
    else:
        log(f"Регистрация {role}", False, r.text)
        sys.exit(1)
    # Получение токена
    r2 = session.post(f"{BASE_URL}/auth/token/", json={'username': creds['username'], 'password': creds['password']})
    if r2.status_code == 200:
        log(f"Вход {role}", True, "")
        return r2.json().get('access')
    else:
        log(f"Вход {role}", False, r2.text)
        sys.exit(1)


admin_token = register_and_login(ADMIN_CRED, 'admin')
user_token = register_and_login(USER_CRED, 'user')

# Повышаем пользователя admin до staff прямо в БД
try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("UPDATE auth_user SET is_staff = TRUE WHERE username = %s", (ADMIN_CRED['username'],))
    conn.commit()
    cur.close()
    conn.close()
    log('Повышение до администратора', True, "")
except Exception as e:
    log('Повышение до администратора', False, str(e))
    sys.exit(1)

# Заголовки авторизации
admin_headers = {'Authorization': 'Bearer ' + admin_token}
user_headers = {'Authorization': 'Bearer ' + user_token}


def clean_db():
    import psycopg2
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    # очищаем все комнаты и брони, сбрасываем счётчики id
    cur.execute("TRUNCATE TABLE booking_booking RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE booking_room RESTART IDENTITY CASCADE;")
    conn.commit()
    cur.close()
    conn.close()
    log('Очистка БД', True, "")


clean_db()


# 1. CRUD-тест для Room
def test_rooms():
    base = f"{BASE_URL}/rooms/"
    # попытка создания комнаты обычным пользователем
    r = session.post(base, json={'name': 'R1', 'capacity': 5, 'floor': 1}, headers=user_headers)
    log('Создание комнаты обычным пользователем', r.status_code == 403, f"status={r.status_code}, body={r.text}")
    # создание комнаты администратором
    r2 = session.post(base, json={'name': 'R1', 'capacity': 5, 'floor': 1}, headers=admin_headers)
    ok = (r2.status_code == 201)
    log('Создание комнаты администратором', ok, f"status={r2.status_code}, body={r2.text}")
    if not ok:
        sys.exit(1)
    room_id = r2.json().get('id')
    # просмотр списка комнат
    r3 = session.get(base, params={'limit': 1000}, headers=user_headers)
    data = r3.json()
    rooms = data.get('results') if isinstance(data, dict) and 'results' in data else []
    ok = (r3.status_code == 200 and any(rm.get('id') == room_id for rm in rooms))
    log('Просмотр списка комнат', ok, f"status={r3.status_code}, body={data}")
    # обновление комнаты
    r4 = session.patch(f"{base}{room_id}/", json={'capacity': 10}, headers=admin_headers)
    ok = (r4.status_code == 200 and r4.json().get('capacity') == 10)
    log('Обновление комнаты', ok, f"status={r4.status_code}, body={r4.text}")
    # удаление комнаты
    r5 = session.delete(f"{base}{room_id}/", headers=admin_headers)
    log('Удаление комнаты', r5.status_code == 204, r5.text)
    return room_id


# 2. Тест свободных комнат (free-rooms)
def test_free_rooms():
    # создаём новую комнату
    unique = f"R2_{int(time.time())}"
    r = session.post(f"{BASE_URL}/rooms/", json={'name': unique, 'capacity': 3, 'floor': 2}, headers=admin_headers)
    if r.status_code == 201:
        room2 = r.json().get('id')
        log('Создание комнаты для free-rooms', True, unique)
    else:
        log('Создание комнаты для free-rooms', False, r.text)
        sys.exit(1)
    # выбираем уникальную дату, чтобы не было конфликтов
    slot_date = date.today() + timedelta(days=random.randint(1, 60))
    params = {
        'date': slot_date.isoformat(),
        'start_time': '09:00:00',
        'end_time': '10:00:00'
    }
    # free-rooms до бронирования
    r1 = session.get(f"{BASE_URL}/rooms/free/", params={**params, 'limit': 1000}, headers=user_headers)
    log('Free-rooms до бронирования', r1.status_code == 200, f"status={r1.status_code}, body={r1.json()}")
    # создаём бронь
    r2 = session.post(f"{BASE_URL}/bookings/",
                      json={'room': room2, 'date': params['date'], 'start_time': params['start_time'],
                            'end_time': params['end_time']}, headers=user_headers)
    ok = (r2.status_code == 201)
    info = '' if ok else f"status={r2.status_code}, response={r2.text}"
    log('Создание брони для free-rooms', ok, f"status={r2.status_code}, body={r2.json()}")
    # free-rooms после бронирования
    r3 = session.get(f"{BASE_URL}/rooms/free/", params={**params, 'limit': 1000}, headers=user_headers)
    results_free = r3.json().get('results', [])
    ok = (r3.status_code == 200 and all(rm['id'] != room2 for rm in results_free))
    info = '' if ok else f"status={r3.status_code}, returned_ids={[rm['id'] for rm in results_free]}, full_response={r3.json()}"
    log('Free-rooms после бронирования', ok, info)


# 3. CRUD-тест для Booking
def test_bookings():
    # создаём новую комнату
    unique = f"R3_{int(time.time())}"
    r = session.post(f"{BASE_URL}/rooms/", json={'name': unique, 'capacity': 4, 'floor': 3}, headers=admin_headers)
    if r.status_code == 201:
        room3 = r.json().get('id')
        log('Создание комнаты для брони', True, unique)
    else:
        log('Создание комнаты для брони', False, r.text)
        sys.exit(1)
    # создание брони
    r1 = session.post(f"{BASE_URL}/bookings/",
                      json={'room': room3, 'date': '2025-06-01', 'start_time': '10:00:00', 'end_time': '11:00:00'},
                      headers=user_headers)
    ok = (r1.status_code == 201)
    log('Создание брони', ok, f"status={r1.status_code}, body={r1.json()}")
    bid = r1.json().get('id') if ok else None
    # конфликт брони
    r2 = session.post(f"{BASE_URL}/bookings/",
                      json={'room': room3, 'date': '2025-06-01', 'start_time': '10:30:00', 'end_time': '11:30:00'},
                      headers=user_headers)
    log('Конфликт брони', r2.status_code == 400, f"status={r2.status_code}, body={r2.text}")
    # просмотр бронирований пользователем
    r3 = session.get(f"{BASE_URL}/bookings/", headers=user_headers)
    bs = r3.json().get('results', [])
    ok = (r3.status_code == 200 and bid in [b['id'] for b in bs])
    log('Просмотр бронирований пользователем', ok, f"status={r3.status_code}, body={r3.json()}")
    # просмотр бронирований администратором
    r4 = session.get(f"{BASE_URL}/bookings/", headers=admin_headers)
    bs2 = r4.json().get('results', [])
    ok = (r4.status_code == 200 and bid in [b['id'] for b in bs2])
    log('Просмотр бронирований администратором', ok, f"status={r4.status_code}, body={r4.json()}")
    # обновление брони
    r5 = session.patch(f"{BASE_URL}/bookings/{bid}/", json={'end_time': '11:15:00'}, headers=user_headers)
    ok = (r5.status_code == 200 and r5.json().get('end_time') == '11:15:00')
    log('Обновление брони', ok, f"status={r5.status_code}, body={r5.json()}")
    # удаление брони
    r6 = session.delete(f"{BASE_URL}/bookings/{bid}/", headers=user_headers)
    log('Удаление брони', r6.status_code == 204, f"status={r6.status_code}, body={r6.text}")


# 4. Запуск тестов
room_id = test_rooms()
test_free_rooms()
test_bookings()


# 5. Нагрузочный тест free-rooms
def load_test_free(concurrency=10, per_thread=10):
    def worker(_):
        count = 0
        params = {'date': '2025-07-01', 'start_time': '08:00:00', 'end_time': '09:00:00'}
        for __ in range(per_thread):
            resp = session.get(f"{BASE_URL}/rooms/free/", params=params, headers=user_headers)
            if resp.status_code == 200:
                count += 1
            time.sleep(random.random() * 0.1)
        return count

    total = 0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for c in ex.map(worker, range(concurrency)):
            total += c
    print(f"Нагрузочный тест free-rooms: {total}/{concurrency * per_thread} успехов")


load_test_free()

# 6. Вывод сводки
passes = sum(1 for _, ok, _ in results if ok)
fails = len(results) - passes
print(f"\n=== Итог: успешно {passes}, провалилось {fails} ===")
