from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi.params import Security
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth import UserAlreadyExists, UnknownException, get_token, PasswordIsIncorrect, UserDoesNotExists, \
    create_user, delete_token, refresh_token, get_user_info
from middleware.auth import authorization
from schemas import UserRegisterBody, UserRegisterResponse, UserLoginBody, AccessTokenResponse, User
from services.database import get_db

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", summary="Register a new user")
async def auth_register(
    data: UserRegisterBody,
    session: AsyncSession = Depends(get_db),
) -> UserRegisterResponse:
    """
    Endpoint allows to register a new user. Need to pass username and sha256 of password
    """
    try:
        user = await create_user(session, data)
    except UserAlreadyExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except UnknownException:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return user


@auth_router.post("/login", summary="Login user and get access token")
async def auth_login(
    data: UserLoginBody,
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """
    Endpoint allows to log in an existing user. Need to pass username and sha256 of password
    """
    try:
        token = await get_token(session, data)
    except PasswordIsIncorrect:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except UserDoesNotExists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return token


@auth_router.post("/logout", summary="Logout user")
async def auth_logout(
    user: Annotated[User, Security(authorization())],
    session: AsyncSession = Depends(get_db),
) -> Response:
    """
    Endpoint allows to log out (make opaque token invalid for) a new user.
    """
    try:
        await delete_token(session, user.id)
    except UserDoesNotExists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return Response(status_code=status.HTTP_200_OK)


@auth_router.post("/refresh", summary="Refresh access token")
async def auth_refresh(
    user: Annotated[User, Security(authorization())],
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """
    Endpoint allows to refresh token of a user.
    """
    try:
        new_token = await refresh_token(session, user.id)
    except UserDoesNotExists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return new_token


@auth_router.get("/me", summary="Return user info")
async def auth_verify(
    user: Annotated[User, Security(authorization())],
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint allows to get info about a user. Returns username and token lifetime.
    """
    try:
        info = await get_user_info(session, user.id)
    except UserDoesNotExists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return info


@auth_router.post("/auth/oauth/{provider}", summary="OAuth access token")
async def auth_me():
    """
    Endpoint is not implemented yet. Will allow to authenticate using foreign services.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,)

