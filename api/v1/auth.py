from fastapi import APIRouter, HTTPException
from starlette import status

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/register", summary="Register a new user")
async def auth_register():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)


@auth_router.post("/login", summary="Login user and get access token")
async def auth_login():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)


@auth_router.post("/logout", summary="Logout user")
async def auth_logout():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)


@auth_router.post("/refresh", summary="Refresh access token")
async def auth_refresh():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)


@auth_router.get("/me", summary="Return user info")
async def auth_verify():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)


@auth_router.post("/auth/oauth/{provider}", summary="OAuth access token")
async def auth_me():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)

