# booking/cron.py

from django.core.management import call_command
from django.db import connection


def run_partition_manager():
    """
    Запускает команду pgpartition (psqlextra) для создания/поддержки партиций.
    """
    call_command("pgpartition", verbosity=0)


def db_maintenance():
    """
    Выполняет VACUUM ANALYZE и CLUSTER по индексу idx_date_start_end_room для ускорения выборок.
    """
    with connection.cursor() as cursor:
        # VACUUM ANALYZE всей таблицы
        cursor.execute("VACUUM ANALYZE booking_booking;")
        # CLUSTER по индексу для улучшения физической упорядоченности
        cursor.execute("CLUSTER booking_booking USING idx_date_start_end_room;")
