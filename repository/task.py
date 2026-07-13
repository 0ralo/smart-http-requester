import uuid
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import text, BindParameter, TEXT, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID as UUIDType, JSONB

from schemas import TaskCreate, TaskResponse
import json
from services.redis_service import get_redis


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self,
        user_id: int,
        url: str,
        method: str,
        headers: Optional[dict],
        body: Optional[str],
        max_attempts: int,
        status: str = 'pending'
    ) -> TaskResponse:
        """Create a new task in the database"""
        query = await self.session.execute(text("""
            INSERT INTO tasks (user_id, url, method, headers, body, max_attempts, status, attempt_count)
            VALUES (:user_id, :url, :method, :headers, :body, :max_attempts, :status, 0)
            RETURNING id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
        """).bindparams(
            BindParameter("user_id", user_id, Integer),
            BindParameter("url", url, TEXT),
            BindParameter("method", method, TEXT),
            BindParameter("headers", headers, JSONB),
            BindParameter("body", body, TEXT),
            BindParameter("max_attempts", max_attempts, Integer),
            BindParameter("status", status, TEXT),
        ))
        raw_task = query.fetchone()
        return TaskResponse.model_validate(raw_task)

    async def get_task_by_id(self, task_id: UUID) -> Optional[tuple[TaskResponse, int]]:
        """Get task by ID with user_id for ownership check"""
        query = await self.session.execute(text("""
            SELECT id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
            FROM tasks
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", task_id, UUIDType),
        ))
        raw_task = query.fetchone()
        if raw_task is None:
            return None
        # Return both the TaskResponse and user_id for ownership check
        user_id = raw_task.user_id
        task = TaskResponse.model_validate(raw_task)
        return task, user_id

    async def create_tasks_batch(
        self,
        user_id: int,
        tasks_data: list[TaskCreate],
    ) -> list[TaskResponse]:
        """Create multiple tasks in a single database transaction."""
        if not tasks_data:
            return []

        values = []
        bindparams = [BindParameter("user_id", user_id, Integer)]

        for idx, task in enumerate(tasks_data):
            values.append(
                f"(:user_id, :url_{idx}, :method_{idx}, :headers_{idx}, :body_{idx}, :max_attempts_{idx}, 'pending', 0)"
            )
            bindparams.extend([
                BindParameter(f"url_{idx}", task.url, TEXT),
                BindParameter(f"method_{idx}", task.method, TEXT),
                BindParameter(f"headers_{idx}", task.headers, JSONB),
                BindParameter(f"body_{idx}", task.body, TEXT),
                BindParameter(f"max_attempts_{idx}", task.max_attempts, Integer),
            ])

        query = await self.session.execute(text(f"""
            INSERT INTO tasks (user_id, url, method, headers, body, max_attempts, status, attempt_count)
            VALUES {', '.join(values)}
            RETURNING id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
        """).bindparams(*bindparams))

        raw_tasks = query.fetchall()
        return [TaskResponse.model_validate(task) for task in raw_tasks]

    async def get_user_tasks(self, user_id: int, skip: int = 0, limit: int = 20) -> list[TaskResponse]:
        """Get all tasks for a user with pagination, sorted by updated_at (desc) or created_at"""
        query = await self.session.execute(text("""
            SELECT id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
            FROM tasks
            WHERE user_id = :user_id
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT :limit OFFSET :skip
        """).bindparams(
            BindParameter("user_id", user_id, Integer),
            BindParameter("skip", skip, Integer),
            BindParameter("limit", limit, Integer),
        ))
        raw_tasks = query.fetchall()
        return [TaskResponse.model_validate(task) for task in raw_tasks]

    async def cancel_task(self, task_id: UUID) -> Optional[tuple[TaskResponse, int, str]]:
        """
        Cancel task by setting status to canceled. 
        Returns tuple (TaskResponse, user_id, old_status) if successful, None if task not found
        """
        # First get the current status and user_id
        query = await self.session.execute(text("""
            SELECT user_id, status
            FROM tasks
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", task_id, UUIDType),
        ))
        result = query.fetchone()
        if result is None:
            return None
        
        user_id = result.user_id
        current_status = result.status
        
        # Update only if status is pending
        if current_status == 'pending':
            await self.session.execute(text("""
                UPDATE tasks
                SET status = 'canceled', updated_at = NOW()
                WHERE id = :task_id
            """).bindparams(
                BindParameter("task_id", task_id, UUIDType),
            ))
        
        # Get updated task info
        query = await self.session.execute(text("""
            SELECT id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
            FROM tasks
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", task_id, UUIDType),
        ))
        raw_task = query.fetchone()
        task = TaskResponse.model_validate(raw_task)
        
        # publish status change if it happened
        try:
            new_status = task.status
            if current_status != new_status:
                payload = json.dumps({"task_id": str(task.id), "status": new_status})
                redis = await get_redis()
                await redis.publish("tasks.status", payload)
        except Exception:
            # don't fail DB operations if publishing failed
            pass

        return task, user_id, current_status

    async def update_task(
        self,
        task_id: UUID,
        url: str,
        method: str,
        headers: Optional[dict],
        body: Optional[str],
    ) -> Optional[tuple[TaskResponse, int, str]]:
        """
        Update task data (only url, method, headers, body).
        Returns tuple (TaskResponse, user_id, status) if successful, None if task not found
        """
        # Get current status and user_id
        query = await self.session.execute(text("""
            SELECT user_id, status
            FROM tasks
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", task_id, UUIDType),
        ))
        result = query.fetchone()
        if result is None:
            return None
        
        user_id = result.user_id
        current_status = result.status
        
        # Update task
        await self.session.execute(text("""
            UPDATE tasks
            SET url = :url, method = :method, headers = :headers, body = :body, updated_at = NOW()
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", task_id, UUIDType),
            BindParameter("url", url, TEXT),
            BindParameter("method", method, TEXT),
            BindParameter("headers", headers, JSONB),
            BindParameter("body", body, TEXT),
        ))
        
        # Get updated task info
        query = await self.session.execute(text("""
            SELECT id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
            FROM tasks
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", task_id, UUIDType),
        ))
        raw_task = query.fetchone()
        task = TaskResponse.model_validate(raw_task)
        
        # If status changed (unlikely here), publish update
        try:
            new_status = task.status
            if current_status != new_status:
                payload = json.dumps({"task_id": str(task.id), "status": new_status})
                redis = await get_redis()
                await redis.publish("tasks.status", payload)
        except Exception as e:
            logger.error(f"Error while processing task: {e}")

        return task, user_id, current_status

    async def confirm_rmq_task(self, id: uuid.UUID):
        await self.session.execute(text("""
            update tasks set status = 'pending' where id=:id and status = 'BEFORE RMQ'
        """).bindparams(
            BindParameter("id", id, UUIDType),
        ))

