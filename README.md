# Booking API

## Обзор
Приложение "Booking API" предоставляет REST‑интерфейс для управления переговорными комнатами и бронированием. Позволяет:

- Администратору создавать, редактировать и удалять комнаты.
- Аутентифицированным пользователям просматривать список комнат и бронировать их.
- Запрашивать свободные комнаты по дате и времени.
- Использовать JWT‑токены для аутентификации.
- Документация Swagger доступна по `/swagger/`.

## Стек технологий

- Python 3 и Django 4.2
- Django REST Framework
- PostgreSQL с поддержкой партицирования (psqlextra)
- Docker, docker‑compose
- Simple JWT для аутентификации
- drf‑yasg для Swagger

## Подготовка и запуск

1. Клонируйте репозиторий:
   ```bash
   git clone <url> booking-api
   cd booking-api
   ```

2. Создайте файл `.env` в корне проекта с переменными окружения:
   ```dotenv
   POSTGRES_USER=booking
   POSTGRES_PASSWORD=booking
   POSTGRES_DB=booking
   DB_HOST=db-master
   DB_PORT=5432

   REPLICA_DB_HOST=db-replica
   REPLICA_DB_PORT=5432

   SECRET_KEY=<ваш django SECRET_KEY>
   DEBUG=True
   ```

3. Запустите контейнеры:
   ```bash
   docker-compose up -d --build
   ```

4. (Опционально) Создайте суперпользователя:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## Доступные сервисы

- **db-master**: основной PostgreSQL на порту 5432
- **db-replica**: реплика PostgreSQL на порту 5433
- **web**: Django-приложение на порту 8000

## Эндпоинты API

### Аутентификация

| Метод | URL                       | Описание                                    |
|-------|---------------------------|---------------------------------------------|
| POST  | `/api/auth/register/`     | Регистрация нового пользователя             |
| POST  | `/api/auth/token/`        | Получение JWT‑токена                        |
| POST  | `/api/auth/token/refresh/`| Обновление JWT‑токена                       |

### Комнаты (Rooms)

| Метод      | URL                    | Права              | Описание                                |
|------------|------------------------|-------------------|-----------------------------------------|
| GET        | `/api/rooms/`          | Любой аутентиф.     | Список всех комнат (пагинация)         |
| POST       | `/api/rooms/`          | Администратор      | Создание новой комнаты                  |
| GET        | `/api/rooms/{id}/`     | Любой аутентиф.     | Детальная информация о комнате          |
| PATCH      | `/api/rooms/{id}/`     | Администратор      | Частичное обновление комнаты            |
| DELETE     | `/api/rooms/{id}/`     | Администратор      | Удаление комнаты                        |
| GET        | `/api/rooms/free/`     | Любой аутентиф.     | Список свободных комнат<br>`?date=YYYY-MM-DD&start_time=HH:MM:SS&end_time=HH:MM:SS[&floor][&capacity]` |

### Бронирования (Bookings)

| Метод      | URL                    | Права               | Описание                            |
|------------|------------------------|---------------------|-------------------------------------|
| GET        | `/api/bookings/`       | Пользователь        | Список своих бронирований (пагинация)<br>Админ видит все |
| POST       | `/api/bookings/`       | Пользователь        | Создание бронирования               |
| GET        | `/api/bookings/{id}/`  | Владелец/админ       | Детали бронирования                 |
| PATCH      | `/api/bookings/{id}/`  | Владелец            | Частичное обновление брони          |
| DELETE     | `/api/bookings/{id}/`  | Владелец            | Удаление бронирования               |

### Дополнительно

- Swagger UI: http://localhost:8000/swagger/
- Redoc:       http://localhost:8000/redoc/
- Django Admin: http://localhost:8000/admin/

## Рекомендации

- В `production` отключите `DEBUG` и настройте `ALLOWED_HOSTS`.
- Используйте cron‑job для `pgpartition` и `VACUUM ANALYZE` (настроено через `django_crontab`).

---

*Автор: команда разработчиков*

