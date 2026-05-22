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
