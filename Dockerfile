FROM python:3.14-slim

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копировать зависимости
COPY pyproject.toml .

# Установить Python зависимости
RUN pip install --no-cache-dir -e .

# Копировать приложение
COPY . .

# Создать директорию для логов
RUN mkdir -p logs

# Запустить приложение
CMD ["python", "-m", "uvicorn", "application:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
