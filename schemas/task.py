import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class BaseModelFromAttributes(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )


class TaskCreate(BaseModel):
    url: HttpUrl
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    headers: Optional[dict[str, str]] = None
    body: Optional[str] = None
    max_attempts: int = Field(default=5, le=20)


class TaskUpdate(BaseModel):
    url: HttpUrl
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    headers: Optional[dict[str, str]] = None
    body: Optional[str] = None


class TaskResponse(BaseModelFromAttributes):
    id: UUID
    url: HttpUrl
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    headers: Optional[dict[str, str]]
    body: Optional[str]
    status: str
    attempt_count: int
    max_attempts: int
    result: Optional[dict]
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
