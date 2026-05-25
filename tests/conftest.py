"""Pytest configuration and shared fixtures."""
import hashlib
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Patch external services before importing app
with patch("services.redis.get_redis"), \
     patch("services.redis.close_redis"), \
     patch("services.database.database_ping"), \
     patch("services.rabbitmq.get_rabbitmq"), \
     patch("services.rabbitmq.close_rabbitmq"):
    from application import app as fastapi_app

from domain.auth import UserAlreadyExists, UnknownException, PasswordIsIncorrect, UserDoesNotExists
from schemas import UserRegisterBody, UserLoginBody, UserRegisterResponse, AccessTokenResponse


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite async session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(lambda: None)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def valid_username() -> str:
    """Fixture for a valid username."""
    return "testuser"


@pytest.fixture
def valid_password() -> str:
    """Fixture for a valid password."""
    return "securepassword123"


@pytest.fixture
def valid_password_hash(valid_password: str) -> str:
    """Fixture for a valid SHA256 password hash (64 hex characters)."""
    return hashlib.sha256(valid_password.encode()).hexdigest()


@pytest.fixture
def invalid_password_hash() -> str:
    """Fixture for an invalid password hash (wrong length)."""
    return "abc"  # Too short, must be 64 chars


@pytest.fixture
def register_body(valid_username: str, valid_password_hash: str) -> UserRegisterBody:
    """Fixture for a valid registration request body."""
    return UserRegisterBody(username=valid_username, password_hash=valid_password_hash)


@pytest.fixture
def login_body(valid_username: str, valid_password_hash: str) -> UserLoginBody:
    """Fixture for a valid login request body."""
    return UserLoginBody(username=valid_username, password_hash=valid_password_hash)


@pytest.fixture
def mock_user_response() -> UserRegisterResponse:
    """Fixture for a mocked user registration response."""
    return UserRegisterResponse(user_id=1, username="testuser")


@pytest.fixture
def mock_token_response() -> AccessTokenResponse:
    """Fixture for a mocked token response."""
    return AccessTokenResponse(
        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        token_type="Bearer"
    )


@pytest.fixture
def mock_create_user_success(mock_user_response: UserRegisterResponse):
    """Mock create_user that succeeds."""
    async def mock_impl(*args, **kwargs):
        return mock_user_response
    return AsyncMock(side_effect=mock_impl)


@pytest.fixture
def mock_create_user_already_exists():
    """Mock create_user that raises UserAlreadyExists."""
    async def mock_impl(*args, **kwargs):
        raise UserAlreadyExists
    return AsyncMock(side_effect=mock_impl)


@pytest.fixture
def mock_create_user_error():
    """Mock create_user that raises UnknownException."""
    async def mock_impl(*args, **kwargs):
        raise UnknownException
    return AsyncMock(side_effect=mock_impl)


@pytest.fixture
def mock_get_token_success(mock_token_response: AccessTokenResponse):
    """Mock get_token that succeeds."""
    async def mock_impl(*args, **kwargs):
        return mock_token_response
    return AsyncMock(side_effect=mock_impl)


@pytest.fixture
def mock_get_token_wrong_password():
    """Mock get_token that raises PasswordIsIncorrect."""
    async def mock_impl(*args, **kwargs):
        raise PasswordIsIncorrect
    return AsyncMock(side_effect=mock_impl)


@pytest.fixture
def mock_get_token_user_not_found():
    """Mock get_token that raises UserDoesNotExists."""
    async def mock_impl(*args, **kwargs):
        raise UserDoesNotExists
    return AsyncMock(side_effect=mock_impl)


@pytest.fixture
def mock_metrics():
    """Mock the metrics module."""
    mock_obj = MagicMock()
    mock_obj.labels.return_value.inc = MagicMock()
    with patch("api.v1.auth.auth_attempts_total", mock_obj):
        yield mock_obj


@pytest.fixture
def app() -> FastAPI:
    """Provide FastAPI app instance."""
    return fastapi_app
