from fastapi import APIRouter, HTTPException
from starlette import status

requests_router = APIRouter(prefix="/requests")

@requests_router.post("/", summary="Create HTTP request task")
async def request_create():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.get("/{task_id}", summary="Get task information")
async def request_info():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.get("/", summary="Get current user tasks")
async def request_user_tasks():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


@requests_router.delete("/{task_id}", summary="Delete task fron queue")
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
