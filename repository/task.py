from typing import Optional
from uuid import UUID

from sqlalchemy import text, BindParameter, TEXT, Integer, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID as UUIDType

from schemas import TaskResponse


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
    ) -> TaskResponse:
        """Create a new task in the database"""
        query = await self.session.execute(text("""
            INSERT INTO tasks (user_id, url, method, headers, body, max_attempts, status, attempt_count)
            VALUES (:user_id, :url, :method, :headers, :body, :max_attempts, 'pending', 0)
            RETURNING id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
        """).bindparams(
            BindParameter("user_id", user_id, Integer),
            BindParameter("url", url, TEXT),
            BindParameter("method", method, TEXT),
            BindParameter("headers", headers, JSONB),
            BindParameter("body", body, TEXT),
            BindParameter("max_attempts", max_attempts, Integer),
        ))
        await self.session.commit()
        raw_task = query.fetchone()
        return TaskResponse.model_validate(raw_task)

    async def get_task_by_id(self, task_id: UUID) -> Optional[tuple[TaskResponse, int]]:
        """Get task by ID with user_id for ownership check"""
        query = await self.session.execute(text("""
            SELECT id, user_id, url, method, headers, body, status, attempt_count, max_attempts, result, created_at, updated_at
            FROM tasks
            WHERE id = :task_id
        """).bindparams(
            BindParameter("task_id", str(task_id), TEXT),
        ))
        raw_task = query.fetchone()
        if raw_task is None:
            return None
        # Return both the TaskResponse and user_id for ownership check
        user_id = raw_task.user_id
        task = TaskResponse.model_validate(raw_task)
        return task, user_id

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
