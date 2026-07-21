from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, status, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from middleware.auth import authorization, is_str_uuid
from domain.tasks import (
    create_request_task,
    create_request_tasks_batch,
    get_request_task,
    get_user_request_tasks,
    cancel_request_task,
    update_request_task,
    TaskNotFoundError,
    AccessDeniedError,
    InvalidTaskStatusError,
)
from repository import AuthRepository
from schemas import TaskCreate, TaskResponse, User, TaskUpdate
from services.database import get_db, async_session
from services.logger import logger


async def _get_token_from_websocket(websocket: WebSocket) -> str | None:
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return websocket.query_params.get("token")


async def _authenticate_websocket(websocket: WebSocket) -> User | None:
    token = await _get_token_from_websocket(websocket)
    if token is None or not is_str_uuid(token):
        return None

    async with async_session() as session:
        repo = AuthRepository(session)
        user = await repo.get_user_by_token(token)
    return User.model_validate(user) if user is not None else None


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
    logger.info(
        "Task creation requested by user_id=%s for url=%s", user.id, task_data.url
    )
    try:
        task = await create_request_task(user.id, task_data, session)
        logger.info(
            "Task created successfully: task_id=%s user_id=%s", task.id, user.id
        )
    except Exception as exc:
        logger.exception("Task creation failed for user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )

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
    logger.info("Task lookup requested: task_id=%s user_id=%s", task_id, user.id)
    try:
        task = await get_request_task(task_id, user.id, session)
        logger.debug("Task lookup succeeded: task_id=%s user_id=%s", task_id, user.id)
    except TaskNotFoundError:
        logger.warning("Task lookup failed: task_id=%s not found", task_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except AccessDeniedError:
        logger.warning("Task lookup denied: task_id=%s user_id=%s", task_id, user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    return task


@requests_router.get("/", summary="Get current user tasks")
async def request_user_tasks(
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
    skip: Annotated[int, Query(ge=0, description="Number of tasks to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of tasks to return")
    ] = 20,
) -> list[TaskResponse]:
    """
    Get all tasks for the current user with pagination.

    Tasks are sorted by update time (descending), showing most recently modified first.

    - **skip**: Number of tasks to skip (for pagination) - default: 0
    - **limit**: Number of tasks to return (1-100) - default: 20
    """
    logger.info("Listing tasks for user_id=%s skip=%s limit=%s", user.id, skip, limit)
    tasks = await get_user_request_tasks(
        user.id, skip=skip, limit=limit, session=session
    )
    logger.debug("Listed %s tasks for user_id=%s", len(tasks), user.id)
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
    logger.info("Task cancellation requested: task_id=%s user_id=%s", task_id, user.id)
    try:
        task = await cancel_request_task(task_id, user.id, session)
        logger.info(
            "Task canceled successfully: task_id=%s user_id=%s", task_id, user.id
        )
    except TaskNotFoundError:
        logger.warning("Task cancellation failed: task_id=%s not found", task_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except AccessDeniedError:
        logger.warning(
            "Task cancellation denied: task_id=%s user_id=%s", task_id, user.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    except InvalidTaskStatusError as exc:
        logger.warning(
            "Task cancellation rejected: task_id=%s user_id=%s reason=%s",
            task_id,
            user.id,
            exc,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

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
    logger.info("Task update requested: task_id=%s user_id=%s", task_id, user.id)
    try:
        task = await update_request_task(task_id, user.id, task_data, session)
        logger.info(
            "Task updated successfully: task_id=%s user_id=%s", task_id, user.id
        )
    except TaskNotFoundError:
        logger.warning("Task update failed: task_id=%s not found", task_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except AccessDeniedError:
        logger.warning("Task update denied: task_id=%s user_id=%s", task_id, user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    except InvalidTaskStatusError as exc:
        logger.warning(
            "Task update rejected: task_id=%s user_id=%s reason=%s",
            task_id,
            user.id,
            exc,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return task


@requests_router.post("/batch", summary="Create multiple tasks")
async def request_create_batch(
    tasks_data: list[TaskCreate],
    user: Annotated[User, Depends(authorization())],
    session: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """
    Create multiple HTTP request tasks in one database transaction.

    Accepts a JSON array of task objects and returns the created tasks.
    """
    logger.info(
        "Batch task creation requested by user_id=%s count=%s", user.id, len(tasks_data)
    )
    try:
        tasks = await create_request_tasks_batch(user.id, tasks_data, session)
        logger.info(
            "Batch task creation succeeded for user_id=%s count=%s", user.id, len(tasks)
        )
    except ValueError as exc:
        logger.warning("Batch task creation rejected for user_id=%s: %s", user.id, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Batch task creation failed for user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )

    return tasks
