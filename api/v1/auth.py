from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi.params import Security
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth import UserAlreadyExists, UnknownException, get_token, PasswordIsIncorrect, UserDoesNotExists, \
    create_user, delete_token, refresh_token, get_user_info, get_token_for_docs
from middleware.auth import authorization
from schemas import UserRegisterBody, UserRegisterResponse, UserLoginBody, AccessTokenResponse, User
from schemas.auth import UserMe
from services.database import get_db
from services.metrics import auth_attempts_total

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", summary="Register a new user")
async def auth_register(
    data: UserRegisterBody,
    session: AsyncSession = Depends(get_db),
) -> UserRegisterResponse:
    """
    Register a new user in the system.
    
    - **username**: Unique username for the new account
    - **password_hash**: SHA256 hash of the password (64 hex characters)
    
    Returns 409 Conflict if username already exists.
    Returns 500 Internal Server Error if registration fails.
    """
    try:
        user = await create_user(session, data)
        auth_attempts_total.labels(type="register", status="success").inc()
    except UserAlreadyExists:
        auth_attempts_total.labels(type="register", status="conflict").inc()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except UnknownException:
        auth_attempts_total.labels(type="register", status="error").inc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return user


@auth_router.post("/login", summary="Login user and get access token")
async def auth_login(
    data: UserLoginBody,
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """
    Authenticate user and retrieve access token.
    
    - **username**: User's username
    - **password_hash**: SHA256 hash of the password
    
    Returns 401 Unauthorized if password is incorrect.
    Returns 404 Not Found if user does not exist.
    """
    try:
        token = await get_token(session, data)
        auth_attempts_total.labels(type="login", status="success").inc()
    except PasswordIsIncorrect:
        auth_attempts_total.labels(type="login", status="unauthorized").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except UserDoesNotExists:
        auth_attempts_total.labels(type="login", status="not_found").inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return token


@auth_router.post("/logout", summary="Logout user")
async def auth_logout(
    user: Annotated[User, Security(authorization())],
    session: AsyncSession = Depends(get_db),
) -> Response:
    """
    Invalidate the current user's access token and log them out.
    
    Requires authentication. After logout, the token will no longer be valid.
    Returns 200 OK on successful logout.
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
    Refresh the current user's access token with a new valid token.
    
    Requires authentication. Extends the token lifetime by 7 days.
    Returns 404 Not Found if user does not exist.
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
) -> UserMe:
    """
    Get information about the current authenticated user.
    
    Requires authentication. Returns user's username and token expiration time.
    """
    try:
        info = await get_user_info(session, user.id)
    except UserDoesNotExists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return info


@auth_router.post("/token", include_in_schema=False)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    try:
        token = await get_token_for_docs(session, form_data.username, form_data.password)
    except PasswordIsIncorrect:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except UserDoesNotExists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return token

