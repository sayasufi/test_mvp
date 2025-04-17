import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from booking.models import Booking

class Command(BaseCommand):
    help = "Проверяет, что ожидаемые партиции Booking созданы"

    def handle(self, *args, **options):
        table = Booking._meta.db_table
        with connection.cursor() as cursor:
            part = connection.introspection.get_partitioned_table(cursor, table)
            if not part:
                raise CommandError(f"Таблица {table} не партиционируется")
            today = datetime.date.today()
            # Проверяем на три ближайших месяца
            for i in range(3):
                dt = today + datetime.timedelta(days=30 * i)
                mon = dt.strftime("%b").lower()
                name = f"{dt.year}_{mon}"
                if not part.partition_by_name(name=name):
                    raise CommandError(f"Не найдено: партиция {name}")
        self.stdout.write(self.style.SUCCESS("✅ Партиции в порядке"))