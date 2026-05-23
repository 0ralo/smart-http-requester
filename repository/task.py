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
            BindParameter("task_id", task_id, UUIDType),
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
            await self.session.commit()
        
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
        await self.session.commit()
        
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
        
        return task, user_id, current_status
