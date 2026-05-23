import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from middleware.auth import authorization
from repository import TaskRepository
from schemas import TaskCreate, TaskResponse, User, TaskUpdate
from services.database import get_db
from services.rabbitmq import publish_task

requests_router = APIRouter(prefix="/requests", tags=["requests"])


@requests_router.post("/", summary="Create HTTP request task")
async def request_create(
    task_data: TaskCreate,
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
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
async def request_info(
    task_id: UUID,
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Get task information by ID.
    
    Returns task details only if it belongs to the current user.
    Returns 403 Forbidden if the task belongs to another user.
    Returns 404 Not Found if the task does not exist.
    """
    repo = TaskRepository(session)
    result = await repo.get_task_by_id(task_id)
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    task, task_user_id = result
    
    if task_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return task


@requests_router.get("/", summary="Get current user tasks")
async def request_user_tasks(
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
    skip: Annotated[int, Query(ge=0, description="Number of tasks to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of tasks to return")] = 20,
) -> list[TaskResponse]:
    """
    Get all tasks for the current user with pagination.
    
    Tasks are sorted by update time (descending), showing most recently modified first.
    
    - **skip**: Number of tasks to skip (for pagination) - default: 0
    - **limit**: Number of tasks to return (1-100) - default: 20
    """
    repo = TaskRepository(session)
    tasks = await repo.get_user_tasks(user.id, skip=skip, limit=limit)
    return tasks


@requests_router.delete("/{task_id}", summary="Delete task from queue")
async def request_delete(
    task_id: UUID,
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Cancel a task and remove it from the processing queue.
    
    Only tasks with 'pending' status can be canceled.
    Sets the task status to 'canceled' and updates the modification time.
    
    Returns the updated task with 'canceled' status.
    Returns 403 Forbidden if the task belongs to another user.
    Returns 404 Not Found if the task does not exist.
    Returns 400 Bad Request if the task is not in pending status.
    """
    repo = TaskRepository(session)
    result = await repo.cancel_task(task_id)
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    task, task_user_id, current_status = result
    
    if task_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    if current_status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task cannot be canceled. Current status: {current_status}. Only pending tasks can be canceled."
        )
    
    return task


@requests_router.put("/{task_id}", summary="Change task data")
async def request_update(
    task_id: UUID,
    task_data: TaskUpdate,
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Update task data.
    
    Only tasks with 'pending' status can be updated.
    Can update: url, method, headers, body.
    Cannot update: max_attempts (use when creating task).
    
    Returns the updated task.
    Returns 403 Forbidden if the task belongs to another user.
    Returns 404 Not Found if the task does not exist.
    Returns 400 Bad Request if the task is not in pending status.
    """
    repo = TaskRepository(session)
    result = await repo.update_task(
        task_id=task_id,
        url=task_data.url,
        method=task_data.method,
        headers=task_data.headers,
        body=task_data.body,
    )
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    task, task_user_id, current_status = result
    
    if task_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    if current_status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task cannot be updated. Current status: {current_status}. Only pending tasks can be updated."
        )
    
    return task


@requests_router.post("/batch", summary="Create multiple tasks")
async def request_create_batch():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.post("/{task_id}/ws", summary="Get websocket real time status of task")
async def request_websocket():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)
