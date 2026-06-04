from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, status, WebSocket, WebSocketDisconnect
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
from services.redis import get_redis
import json


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
    try:
        task = await create_request_task(user.id, task_data, session)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

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
    try:
        task = await get_request_task(task_id, user.id, session)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    except AccessDeniedError:
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
    tasks = await get_user_request_tasks(user.id, skip=skip, limit=limit, session=session)
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
    try:
        task = await cancel_request_task(task_id, user.id, session)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    except AccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except InvalidTaskStatusError as exc:
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
    try:
        task = await update_request_task(task_id, user.id, task_data, session)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    except AccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except InvalidTaskStatusError as exc:
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
    try:
        tasks = await create_request_tasks_batch(user.id, tasks_data, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return tasks


@requests_router.websocket("/{task_id}/ws")
async def request_websocket(task_id: UUID, websocket: WebSocket):
    """Websocket endpoint for real time status updates of a single task."""
    await websocket.accept()

    user = await _authenticate_websocket(websocket)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        async with async_session() as session:
            await get_request_task(task_id, user.id, session)
    except TaskNotFoundError:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return
    except AccessDeniedError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("tasks.status")

    try:
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, (bytes, bytearray)):
                try:
                    payload = json.loads(data.decode())
                except Exception:
                    continue
            else:
                try:
                    payload = json.loads(str(data))
                except Exception:
                    continue

            if payload.get("task_id") != str(task_id):
                continue

            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await pubsub.unsubscribe("tasks.status")
            await pubsub.close()
        except Exception:
            pass
