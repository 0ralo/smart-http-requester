import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseModelFromAttributes(BaseModel):
    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    url: str
    method: str = "GET"
    headers: Optional[dict] = None
    body: Optional[str] = None
    max_attempts: int = Field(default=5, le=20)


class TaskResponse(BaseModelFromAttributes):
    id: UUID
    user_id: int
    url: str
    method: str
    headers: Optional[dict]
    body: Optional[str]
    status: str
    attempt_count: int
    max_attempts: int
    result: Optional[dict]
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
