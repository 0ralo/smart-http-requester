# WebSocket Real-time Task Status Updates

## Architecture

The system uses **Postgres LISTEN/NOTIFY** mechanism for real-time task status updates:

1. **SQL Trigger** (`migrations/0003_task_notify_trigger.sql`): When a task's status changes in the database (by API, worker, or any external process), a trigger fires and sends a `NOTIFY` event to the `task_status_change` channel with the task ID and new status.

2. **Postgres Listener** (`services/pg_poller.py`): A background task connects to Postgres using asyncpg, listens to the `task_status_change` channel, and republishes each notification to a Redis channel `tasks.status`.

3. **WebSocket Endpoint** (`/ws`): Clients connect via WebSocket. The endpoint subscribes to the Redis `tasks.status` channel and forwards all messages to connected clients in real-time.

## Setup

### 1. Apply the Migration

Run the migration to create the trigger and notification function:

```bash
# Using psql directly
psql -h localhost -U dev -d development -f migrations/0003_task_notify_trigger.sql

# Or via your migration tool
```

### 2. Install Dependencies

The new dependency `asyncpg` has been added to `pyproject.toml`:

```bash
pip install asyncpg>=0.30.0
# or if using UV:
uv sync
```

### 3. Start the Application

```bash
uvicorn application:app --reload
```

The application will automatically:
- Start the Postgres LISTEN/NOTIFY listener on startup
- Connect to Redis pub/sub channel
- Accept WebSocket connections at `/ws`

## Testing

### Option 1: Using Python client

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        print("Connected to WebSocket")
        async for message in ws:
            data = json.loads(message)
            print(f"Task {data['task_id']} status: {data['status']}")

asyncio.run(listen())
```

### Option 2: Using psql to manually trigger a status change

In one terminal, run the Python client from Option 1. Then in another terminal:

```bash
psql -h localhost -U dev -d development

-- Get a task ID first
SELECT id FROM tasks LIMIT 1;

-- Update the task status (this triggers the NOTIFY)
UPDATE tasks SET status = 'done' WHERE id = '<task-id-here>';
```

You should see the status update appear in the WebSocket client immediately.

### Option 3: Using `wscat` or similar WebSocket CLI tool

```bash
# Install wscat globally
npm install -g wscat

# Connect to the WebSocket
wscat -c ws://localhost:8000/ws

# In another terminal, update a task via API or DB
curl -X PUT http://localhost:8000/v1/requests/<task-id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com",...}'
```

## How It Works

1. **API Request or Worker Update**: Any process updates a task's `status` field in the `tasks` table.

2. **Postgres Trigger Fires**: The `notify_task_status_change()` function is called, which sends:
   ```
   NOTIFY task_status_change, '{"task_id":"...", "status":"...", "operation":"INSERT/UPDATE"}'
   ```

3. **Listener Receives & Publishes**: The asyncpg listener in `start_pg_listener()` receives the notification and publishes it to Redis:
   ```
   PUBLISH tasks.status '{"task_id":"...", "status":"...", "operation":"..."}'
   ```

4. **WebSocket Clients Receive**: All connected WebSocket clients receive the message via Redis pub/sub.

## Advantages over Polling

- **Real-time**: No polling interval delay; events are sent instantly.
- **Efficient**: No repeated database queries; only actual changes trigger updates.
- **Scalable**: Works with multiple application instances (all listening to the same Postgres notifications).
- **Works with External Workers**: If a worker process (e.g., Celery, Temporal, custom service) updates task status directly in Postgres, the system still captures it.

## Troubleshooting

### WebSocket not receiving updates

1. Check that the trigger was created:
   ```sql
   SELECT trigger_name FROM information_schema.triggers 
   WHERE event_object_table = 'tasks';
   ```

2. Verify Redis is connected:
   ```bash
   redis-cli PING  # Should return PONG
   ```

3. Check application logs for listener errors:
   ```bash
   tail -f logs/app.log | grep "listener\|pg_listener"
   ```

### Postgres connection issues

Ensure asyncpg can connect with your database credentials. The DSN is built from:
- `postgres_user`, `postgres_password`, `postgres_host`, `postgres_port`, `postgres_database` from `.env` or config
