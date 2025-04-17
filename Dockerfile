FROM python:3.11-slim

# Не кэшировать .pyc, сразу выводить логи
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME=/opt/poetry

# Добавляем poetry в PATH
ENV PATH=$POETRY_HOME/bin:$PATH

WORKDIR /app

# Системные зависимости, включая cron
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libpq-dev postgresql-client curl cron \
 && rm -rf /var/lib/apt/lists/*

# Скопировать манифесты
COPY pyproject.toml poetry.lock /app/

# Установить Poetry, зависимости и Gunicorn
RUN curl -sSL https://install.python-poetry.org | python3 - \
 && poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

# Скопировать весь код
COPY . /app/

# Подготовить entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["bash", "/app/entrypoint.sh"]