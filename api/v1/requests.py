import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from core.auth import authorization
from repository import TaskRepository
from schemas import TaskCreate, TaskResponse, User
from services.database import get_db
from services.rabbitmq import publish_task

requests_router = APIRouter(prefix="/requests", tags=["requests"])


@requests_router.post("/", summary="Create HTTP request task", response_model=TaskResponse)
async def request_create(
    task_data: TaskCreate,
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new HTTP request task.
    
    - **url**: The URL to request
    - **method**: HTTP method (GET, POST, etc.) - default: GET
    - **headers**: Optional request headers as dict
    - **body**: Optional request body
    - **max_attempts**: Maximum number of retry attempts (1-20) - default: 5
    """
    # Create task in database
    repo = TaskRepository(session)
    task = await repo.create_task(
        user_id=user.id,
        url=task_data.url,
        method=task_data.method,
        headers=task_data.headers,
        body=task_data.body,
        max_attempts=task_data.max_attempts,
    )
    
    # Publish task to RabbitMQ queue with max_attempts
    payload = json.dumps({
        "task_id": str(task.id)
    })
    await publish_task(payload, attempts=task.max_attempts)
    
    return task


@requests_router.get("/{task_id}", summary="Get task information")
async def request_info():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.get("/", summary="Get current user tasks")
async def request_user_tasks():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.delete("/{task_id}", summary="Delete task from queue")
async def request_delete():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.put("/{task_id}", summary="Change task data")
async def request_update():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.post("/batch", summary="Create multiple tasks")
async def request_create_batch():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.post("/{task_id}/ws", summary="Get websocket real time status of task")
async def request_websocket():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)
