#!/usr/bin/env bash
set -e

# 1. Подождать, пока мастер‑БД станет готовой
echo "⏳ Ждём, пока master Postgres будет готов..."
until pg_isready -h "${DB_HOST:-db-master}" -p "${DB_PORT:-5432}" -U "${POSTGRES_USER:-booking}" > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Master Postgres доступен!"

# 2. Подождать, пока replica‑БД станет готовой (если задана)
if [ -n "${REPLICA_DB_HOST:-}" ]; then
  echo "⏳ Ждём, пока replica Postgres будет готов..."
  until pg_isready -h "${REPLICA_DB_HOST}" -p "${REPLICA_DB_PORT:-5432}" -U "${POSTGRES_USER:-booking}" > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Replica Postgres доступен!"
fi

# 3. Применить все миграции
echo "📦 Применяем миграции..."
python manage.py migrate --no-input

# 4. Создать недостающие партиции
echo "🗂 Создаём недостающие партиции..."
python manage.py pgpartition --yes

# 5. Проверить партиции
echo "🔍 Проверяем партиции..."
python manage.py check_partitions

# 6. Настроить и запустить cron‑демон для задач django-crontab
echo "🔧 Настраиваем cron-задания..."
# Удалим старые, если есть
python manage.py crontab remove || true
# Добавим актуальные
python manage.py crontab add

echo "✅ Cron-задания добавлены!"
# Запускаем демон cron
cron

echo "🧪 Прогоним тесты..."
pytest --maxfail=1 --disable-warnings -q

# 7. Запустить Gunicorn
echo "🚀 Запускаем Gunicorn"
exec gunicorn project.wsgi:application \
     --bind 0.0.0.0:8000 \
     --workers 3

