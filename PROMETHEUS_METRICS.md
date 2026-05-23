# Prometheus Metrics Integration

Этот проект включает интеграцию с Prometheus для сбора метрик HTTP эндпоинтов и операций приложения.

## Доступные метрики

### HTTP Метрики

#### `http_requests_total`
Счетчик всех HTTP запросов.
- **Тип:** Counter
- **Лейблы:** `method`, `endpoint`, `status`
- **Пример:** `http_requests_total{method="POST",endpoint="/v1/requests",status="201"}`

#### `http_request_duration_seconds`
Гистограмма длительности HTTP запросов.
- **Тип:** Histogram
- **Лейблы:** `method`, `endpoint`
- **Бакеты:** 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0 секунд

#### `http_request_size_bytes`
Размер входящих HTTP запросов.
- **Тип:** Histogram
- **Лейблы:** `method`, `endpoint`

#### `http_response_size_bytes`
Размер исходящих HTTP ответов.
- **Тип:** Histogram
- **Лейблы:** `method`, `endpoint`

#### `http_requests_in_progress`
Количество активных HTTP запросов.
- **Тип:** Gauge
- **Лейблы:** `method`, `endpoint`

### Метрики задач (Tasks)

#### `tasks_created_total`
Счетчик созданных задач.
- **Тип:** Counter

#### `tasks_completed_total`
Счетчик завершенных задач.
- **Тип:** Counter
- **Лейблы:** `status` (canceled, completed, failed)

#### `tasks_in_queue`
Количество задач в очереди.
- **Тип:** Gauge

### Метрики аутентификации

#### `auth_attempts_total`
Счетчик попыток аутентификации.
- **Тип:** Counter
- **Лейблы:** `type` (register, login), `status` (success, unauthorized, conflict, not_found, error)

## Использование

### 1. Установка зависимостей

Зависимость `prometheus-client` уже добавлена в `pyproject.toml`:

```bash
pip install -e .
```

### 2. Запуск приложения

```bash
python -m uvicorn application:app --host 0.0.0.0 --port 8000
```

или

```bash
granian --host 0.0.0.0 --port 8000 --interface asgi application:app
```

### 3. Доступ к метрикам

Метрики доступны по адресу: `http://localhost:8000/v1/metrics`

Выведет текст в формате Prometheus:

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/v1/requests",method="POST",status="201"} 42.0
http_requests_total{endpoint="/v1/auth/login",method="POST",status="200"} 15.0
# ... и остальные метрики
```

### 4. Конфигурация Prometheus

Создайте `prometheus.yml` в корне проекта:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'smart-http-requester'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/v1/metrics'
```

### 5. Запуск Prometheus

```bash
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

Prometheus будет доступен по адресу: `http://localhost:9090`

## Примеры запросов Prometheus

### Общее количество запросов по эндпоинтам
```promql
sum by (endpoint) (http_requests_total)
```

### Средняя длительность запроса
```promql
avg(http_request_duration_seconds_bucket)
```

### Количество активных запросов
```promql
http_requests_in_progress
```

### Процент успешных регистраций
```promql
sum(auth_attempts_total{type="register",status="success"}) / 
sum(auth_attempts_total{type="register"})
```

### Ошибки при входе
```promql
sum(auth_attempts_total{type="login",status!="success"})
```

## Middleware

Middleware `MetricsMiddleware` автоматически:
- Отслеживает время выполнения каждого запроса
- Записывает размер запроса и ответа
- Отсчитывает количество активных запросов
- Категоризирует запросы по методу, эндпоинту и коду ответа

ID в URL (UUID) автоматически заменяются на `{id}` для группировки метрик:
- `/requests/550e8400-e29b-41d4-a716-446655440000` → `/requests/{id}`

## Интеграция с инструментами мониторинга

Метрики поддерживают интеграцию с:
- **Prometheus** - прямой скрейп
- **Grafana** - визуализация
- **AlertManager** - оповещения
- **VictoriaMetrics** - долгосрочное хранилище
- **Datadog** - облачный мониторинг (через prometheus agent)

## Примеры Grafana дашбордов

### Базовый дашборд
```json
{
  "panels": [
    {
      "title": "Total Requests",
      "targets": [{"expr": "sum(http_requests_total)"}]
    },
    {
      "title": "Request Duration",
      "targets": [{"expr": "avg(http_request_duration_seconds)"}]
    },
    {
      "title": "Error Rate",
      "targets": [{"expr": "sum(http_requests_total{status=~\"5..\"})/sum(http_requests_total)"}]
    }
  ]
}
```
