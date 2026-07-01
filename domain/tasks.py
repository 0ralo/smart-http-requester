import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from repository import TaskRepository
from schemas import TaskCreate, TaskResponse, TaskUpdate
from services.rabbitmq import publish_task
from services.metrics import tasks_created_total, tasks_completed_total


# Custom exceptions
class TaskNotFoundError(Exception):
    """Task does not exist"""
    pass


class AccessDeniedError(Exception):
    """User does not have access to this task"""
    pass


class InvalidTaskStatusError(Exception):
    """Task is in an invalid state for this operation"""
    pass


async def create_request_task(
    user_id: int,
    task_data: TaskCreate,
    session: AsyncSession,
) -> TaskResponse:
    """
    Create a new HTTP request task and publish it to the queue.
    
    Args:
        user_id: ID of the user creating the task
        task_data: Task creation data (url, method, headers, body, max_attempts)
        session: Database session
        
    Returns:
        Created TaskResponse object
    """
    repo = TaskRepository(session)
    
    # Create task in database
    task = await repo.create_task(
        user_id=user_id,
        url=str(task_data.url),
        method=task_data.method,
        headers=task_data.headers,
        body=task_data.body,
        max_attempts=task_data.max_attempts,
    )
    await session.commit()
    
    # Publish task to RabbitMQ queue
    payload = json.dumps({"task_id": str(task.id)})
    await publish_task(payload, attempts=task.max_attempts)
    
    tasks_created_total.inc()
    return task


async def create_request_tasks_batch(
    user_id: int,
    tasks_data: list[TaskCreate],
    session: AsyncSession,
) -> list[TaskResponse]:
    """
    Create multiple request tasks and publish them to the queue.
    """
    if len(tasks_data) == 0:
        raise ValueError("At least one task must be provided.")

    repo = TaskRepository(session)
    tasks = await repo.create_tasks_batch(
        user_id=user_id,
        tasks_data=tasks_data,
    )

    for task in tasks:
        payload = json.dumps({"task_id": str(task.id)})
        await publish_task(payload, attempts=task.max_attempts)

    tasks_created_total.inc(len(tasks))
    return tasks


async def get_request_task(
    task_id: UUID,
    user_id: int,
    session: AsyncSession,
) -> TaskResponse:
    """
    Get task information with ownership verification.
    
    Args:
        task_id: ID of the task to retrieve
        user_id: ID of the user requesting the task
        session: Database session
        
    Returns:
        TaskResponse object
        
    Raises:
        TaskNotFoundError: Task does not exist
        AccessDeniedError: User does not own the task
    """
    repo = TaskRepository(session)
    result = await repo.get_task_by_id(task_id)
    
    if result is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    
    task, task_user_id = result
    
    if task_user_id != user_id:
        raise AccessDeniedError(f"User does not have access to task {task_id}")
    
    return task


async def get_user_request_tasks(
    user_id: int,
    skip: int,
    limit: int,
    session: AsyncSession,
) -> list[TaskResponse]:
    """
    Get all tasks for a user with pagination.
    
    Args:
        user_id: ID of the user
        skip: Number of tasks to skip
        limit: Number of tasks to return
        session: Database session
        
    Returns:
        List of TaskResponse objects sorted by update time (descending)
    """
    repo = TaskRepository(session)
    tasks = await repo.get_user_tasks(user_id, skip=skip, limit=limit)
    return tasks


async def cancel_request_task(
    task_id: UUID,
    user_id: int,
    session: AsyncSession,
) -> TaskResponse:
    """
    Cancel a task and remove it from the processing queue.
    
    Args:
        task_id: ID of the task to cancel
        user_id: ID of the user requesting cancellation
        session: Database session
        
    Returns:
        Updated TaskResponse with 'canceled' status
        
    Raises:
        TaskNotFoundError: Task does not exist
        AccessDeniedError: User does not own the task
        InvalidTaskStatusError: Task is not in 'pending' status
    """
    repo = TaskRepository(session)
    result = await repo.cancel_task(task_id)
    
    if result is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    
    task, task_user_id, current_status = result
    
    if task_user_id != user_id:
        raise AccessDeniedError(f"User does not have access to task {task_id}")
    
    if current_status != 'pending':
        raise InvalidTaskStatusError(
            f"Task cannot be canceled. Current status: {current_status}. "
            f"Only pending tasks can be canceled."
        )

    tasks_completed_total.labels(status="canceled").inc()
    return task


async def update_request_task(
    task_id: UUID,
    user_id: int,
    task_data: TaskUpdate,
    session: AsyncSession,
) -> TaskResponse:
    """
    Update task data (url, method, headers, body).
    
    Args:
        task_id: ID of the task to update
        user_id: ID of the user requesting the update
        task_data: Updated task data
        session: Database session
        
    Returns:
        Updated TaskResponse
        
    Raises:
        TaskNotFoundError: Task does not exist
        AccessDeniedError: User does not own the task
        InvalidTaskStatusError: Task is not in 'pending' status
    """
    repo = TaskRepository(session)
    result = await repo.update_task(
        task_id=task_id,
        url=str(task_data.url),
        method=task_data.method,
        headers=task_data.headers,
        body=task_data.body,
    )
    
    if result is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    
    task, task_user_id, current_status = result
    
    if task_user_id != user_id:
        raise AccessDeniedError(f"User does not have access to task {task_id}")
    
    if current_status != 'pending':
        raise InvalidTaskStatusError(
            f"Task cannot be updated. Current status: {current_status}. "
            f"Only pending tasks can be updated."
        )
    
    return task
