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
from services.logger import logger
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
    logger.info("Registration requested for username=%s", data.username)
    try:
        user = await create_user(session, data)
        auth_attempts_total.labels(type="register", status="success").inc()
        logger.info("Registration succeeded for username=%s", data.username)
    except UserAlreadyExists:
        auth_attempts_total.labels(type="register", status="conflict").inc()
        logger.warning("Registration failed: username already exists (%s)", data.username)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except UnknownException:
        auth_attempts_total.labels(type="register", status="error").inc()
        logger.exception("Registration failed for username=%s", data.username)
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
    logger.info("Login requested for username=%s", data.username)
    try:
        token = await get_token(session, data)
        auth_attempts_total.labels(type="login", status="success").inc()
        logger.info("Login succeeded for username=%s", data.username)
    except PasswordIsIncorrect:
        auth_attempts_total.labels(type="login", status="unauthorized").inc()
        logger.warning("Login failed: invalid password for username=%s", data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except UserDoesNotExists:
        auth_attempts_total.labels(type="login", status="not_found").inc()
        logger.warning("Login failed: user not found for username=%s", data.username)
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
    logger.info("Logout requested for user_id=%s", user.id)
    try:
        await delete_token(session, user.id)
        logger.info("Logout succeeded for user_id=%s", user.id)
    except UserDoesNotExists:
        logger.warning("Logout failed: user_id=%s not found", user.id)
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
    logger.info("Token refresh requested for user_id=%s", user.id)
    try:
        new_token = await refresh_token(session, user.id)
        logger.info("Token refresh succeeded for user_id=%s", user.id)
    except UserDoesNotExists:
        logger.warning("Token refresh failed: user_id=%s not found", user.id)
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
    logger.info("User profile requested for user_id=%s", user.id)
    try:
        info = await get_user_info(session, user.id)
        logger.debug("User profile fetched for user_id=%s", user.id)
    except UserDoesNotExists:
        logger.warning("User profile fetch failed: user_id=%s not found", user.id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return info


@auth_router.post("/token", include_in_schema=False)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    logger.info("Docs token request for username=%s", form_data.username)
    try:
        token = await get_token_for_docs(session, form_data.username, form_data.password)
        logger.debug("Docs token issued for username=%s", form_data.username)
    except PasswordIsIncorrect:
        logger.warning("Docs token request failed: invalid password for username=%s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except UserDoesNotExists:
        logger.warning("Docs token request failed: user not found for username=%s", form_data.username)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return token

