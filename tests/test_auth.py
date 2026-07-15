"""Tests for authentication endpoints."""
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestAuthRegister:
    """Tests for POST /auth/register endpoint."""

    async def test_register_success(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_user_response,
        mock_metrics,
    ):
        """Test successful user registration."""
        with patch("api.v1.auth.create_user") as mock_create_user:
            mock_create_user.return_value = mock_user_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/register",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["user_id"] == 1
            mock_create_user.assert_called_once()

    async def test_register_username_already_exists(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test registration fails when username already exists."""
        from domain.auth import UserAlreadyExists
        
        with patch("api.v1.auth.create_user") as mock_create_user:
            mock_create_user.side_effect = UserAlreadyExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/register",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 409

    async def test_register_internal_error(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test registration fails with internal server error."""
        from domain.auth import UnknownException
        
        with patch("api.v1.auth.create_user") as mock_create_user:
            mock_create_user.side_effect = UnknownException
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/register",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 500

    async def test_register_invalid_password_hash_length(
        self,
        app,
        valid_username: str,
        mock_metrics,
    ):
        """Test registration fails with invalid password hash length."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/register",
                json={"username": valid_username, "password_hash": "short"}
            )
            
            assert response.status_code == 422  # Validation error

    async def test_register_missing_username(
        self,
        app,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test registration fails when username is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/register",
                json={"password_hash": valid_password_hash}
            )
            
            assert response.status_code == 422

    async def test_register_missing_password(
        self,
        app,
        valid_username: str,
        mock_metrics,
    ):
        """Test registration fails when password_hash is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/register",
                json={"username": valid_username}
            )
            
            assert response.status_code == 422

    async def test_register_metrics_success(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_user_response,
        mock_metrics,
    ):
        """Test that success metrics are recorded."""
        with patch("api.v1.auth.create_user") as mock_create_user:
            mock_create_user.return_value = mock_user_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/register",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 200
            mock_metrics.labels.assert_called_with(type="register", status="success")

    async def test_register_metrics_conflict(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test that conflict metrics are recorded."""
        from domain.auth import UserAlreadyExists
        
        with patch("api.v1.auth.create_user") as mock_create_user:
            mock_create_user.side_effect = UserAlreadyExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/register",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 409
            mock_metrics.labels.assert_called_with(type="register", status="conflict")


@pytest.mark.asyncio
class TestAuthLogin:
    """Tests for POST /auth/login endpoint."""

    async def test_login_success(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_token_response,
        mock_metrics,
    ):
        """Test successful user login."""
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.return_value = mock_token_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/login",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "Bearer"
            mock_get_token.assert_called_once()

    async def test_login_invalid_password(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test login fails with incorrect password."""
        from domain.auth import PasswordIsIncorrect
        
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.side_effect = PasswordIsIncorrect
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/login",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 401

    async def test_login_user_not_found(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test login fails when user does not exist."""
        from domain.auth import UserDoesNotExists
        
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/login",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 404

    async def test_login_invalid_password_hash_format(
        self,
        app,
        valid_username: str,
        mock_metrics,
    ):
        """Test login fails with invalid password hash format."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/login",
                json={"username": valid_username, "password_hash": "invalid"}
            )
            
            assert response.status_code == 422

    async def test_login_missing_username(
        self,
        app,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test login fails when username is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/login",
                json={"password_hash": valid_password_hash}
            )
            
            assert response.status_code == 422

    async def test_login_missing_password(
        self,
        app,
        valid_username: str,
        mock_metrics,
    ):
        """Test login fails when password_hash is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/login",
                json={"username": valid_username}
            )
            
            assert response.status_code == 422

    async def test_login_metrics_success(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_token_response,
        mock_metrics,
    ):
        """Test that success metrics are recorded."""
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.return_value = mock_token_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/login",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 200
            mock_metrics.labels.assert_called_with(type="login", status="success")

    async def test_login_metrics_unauthorized(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test that unauthorized metrics are recorded."""
        from domain.auth import PasswordIsIncorrect
        
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.side_effect = PasswordIsIncorrect
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/login",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 401
            mock_metrics.labels.assert_called_with(type="login", status="unauthorized")

    async def test_login_metrics_not_found(
        self,
        app,
        valid_username: str,
        valid_password_hash: str,
        mock_metrics,
    ):
        """Test that not_found metrics are recorded."""
        from domain.auth import UserDoesNotExists
        
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/login",
                    json={"username": valid_username, "password_hash": valid_password_hash}
                )
            
            assert response.status_code == 404
            mock_metrics.labels.assert_called_with(type="login", status="not_found")

    async def test_login_with_various_usernames(
        self,
        app,
        valid_password_hash: str,
        mock_token_response,
        mock_metrics,
    ):
        """Test login works with different valid usernames."""
        test_usernames = ["john_doe", "user123", "a", "very_long_username_123_xyz"]
        
        with patch("api.v1.auth.get_token") as mock_get_token:
            mock_get_token.return_value = mock_token_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for username in test_usernames:
                    response = await client.post(
                        "/v1/auth/login",
                        json={"username": username, "password_hash": valid_password_hash}
                    )
                    assert response.status_code == 200


@pytest.mark.asyncio
class TestAuthToken:
    """Tests for POST /auth/token endpoint (OAuth2 compatible)."""

    async def test_token_success(
        self,
        app,
        valid_username: str,
        valid_password: str,
        mock_token_response,
        mock_metrics,
    ):
        """Test successful token retrieval via OAuth2 form."""
        with patch("api.v1.auth.get_token_for_docs") as mock_get_token_for_docs:
            mock_get_token_for_docs.return_value = mock_token_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/token",
                    data={"username": valid_username, "password": valid_password}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "Bearer"
            mock_get_token_for_docs.assert_called_once()

    async def test_token_invalid_password(
        self,
        app,
        valid_username: str,
        valid_password: str,
        mock_metrics,
    ):
        """Test token endpoint fails with incorrect password."""
        from domain.auth import PasswordIsIncorrect
        
        with patch("api.v1.auth.get_token_for_docs") as mock_get_token_for_docs:
            mock_get_token_for_docs.side_effect = PasswordIsIncorrect
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/token",
                    data={"username": valid_username, "password": valid_password}
                )
            
            assert response.status_code == 401

    async def test_token_user_not_found(
        self,
        app,
        valid_username: str,
        valid_password: str,
        mock_metrics,
    ):
        """Test token endpoint fails when user does not exist."""
        from domain.auth import UserDoesNotExists
        
        with patch("api.v1.auth.get_token_for_docs") as mock_get_token_for_docs:
            mock_get_token_for_docs.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/token",
                    data={"username": valid_username, "password": valid_password}
                )
            
            assert response.status_code == 404

    async def test_token_missing_username(
        self,
        app,
        valid_password: str,
        mock_metrics,
    ):
        """Test token endpoint fails when username is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/token",
                data={"password": valid_password}
            )
            
            assert response.status_code == 422

    async def test_token_missing_password(
        self,
        app,
        valid_username: str,
        mock_metrics,
    ):
        """Test token endpoint fails when password is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/token",
                data={"username": valid_username}
            )
            
            assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthLogout:
    """Tests for POST /auth/logout endpoint."""

    async def test_logout_success(
        self,
        app,
        mock_user,
        valid_token,
        mock_metrics,
    ):
        """Test successful user logout."""
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.auth.delete_token") as mock_delete_token:
            
            # Create an async generator for get_db
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            # Create AsyncMock for get_user_by_token
            mock_user_obj = MagicMock(
                id=mock_user.id,
                username=mock_user.username,
                privileges=mock_user.privileges
            )
            mock_get_user_by_token.return_value = mock_user_obj
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_delete_token.return_value = None
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/logout",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 200

    async def test_logout_missing_token(
        self,
        app,
        mock_metrics,
    ):
        """Test logout fails when authorization token is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/auth/logout")
            
            assert response.status_code == 401

    async def test_logout_invalid_token(
        self,
        app,
        mock_metrics,
    ):
        """Test logout fails with invalid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/logout",
                headers={"Authorization": "Bearer invalid-token"}
            )
            
            assert response.status_code == 401

    async def test_logout_user_not_found(
        self,
        app,
        valid_token,
        mock_metrics,
    ):
        """Test logout fails when user does not exist."""
        from domain.auth import UserDoesNotExists
        
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.delete_token") as mock_delete_token:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = None  # User not found
            mock_delete_token.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/logout",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 401

    async def test_logout_service_user_not_found(
        self,
        app,
        mock_user,
        valid_token,
        mock_metrics,
    ):
        """Test logout returns 400 when delete_token reports missing user."""
        from domain.auth import UserDoesNotExists

        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.delete_token") as mock_delete_token:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = MagicMock(
                id=mock_user.id,
                username=mock_user.username,
                privileges=mock_user.privileges,
            )
            mock_delete_token.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/logout",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 400


@pytest.mark.asyncio
class TestAuthRefresh:
    """Tests for POST /auth/refresh endpoint."""

    async def test_refresh_success(
        self,
        app,
        mock_user,
        valid_token,
        mock_token_response,
        mock_metrics,
    ):
        """Test successful token refresh."""
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.auth.refresh_token") as mock_refresh:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_user_obj = MagicMock(
                id=mock_user.id,
                username=mock_user.username,
                privileges=mock_user.privileges
            )
            mock_get_user_by_token.return_value = mock_user_obj
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_refresh.return_value = mock_token_response
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/refresh",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "Bearer"

    async def test_refresh_missing_token(
        self,
        app,
        mock_metrics,
    ):
        """Test refresh fails when authorization token is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/auth/refresh")
            
            assert response.status_code == 401

    async def test_refresh_invalid_token(
        self,
        app,
        mock_metrics,
    ):
        """Test refresh fails with invalid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/refresh",
                headers={"Authorization": "Bearer invalid-token"}
            )
            
            assert response.status_code == 401

    async def test_refresh_user_not_found(
        self,
        app,
        valid_token,
        mock_metrics,
    ):
        """Test refresh fails when user does not exist."""
        from domain.auth import UserDoesNotExists
        
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.refresh_token") as mock_refresh:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = None  # User not found
            mock_refresh.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/refresh",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 401

    async def test_refresh_service_user_not_found(
        self,
        app,
        mock_user,
        valid_token,
        mock_metrics,
    ):
        """Test refresh returns 404 when refresh_token reports missing user."""
        from domain.auth import UserDoesNotExists

        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.refresh_token") as mock_refresh:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = MagicMock(
                id=mock_user.id,
                username=mock_user.username,
                privileges=mock_user.privileges,
            )
            mock_refresh.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/refresh",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 404
        """Test refresh fails when user does not exist."""
        from domain.auth import UserDoesNotExists
        
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.refresh_token") as mock_refresh:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = None  # User not found
            mock_refresh.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/auth/refresh",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthMe:
    """Tests for GET /auth/me endpoint."""

    async def test_me_success(
        self,
        app,
        mock_user,
        valid_token,
        mock_user_me,
        mock_metrics,
    ):
        """Test successful retrieval of user info."""
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.auth.get_user_info") as mock_get_info:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_user_obj = MagicMock(
                id=mock_user.id,
                username=mock_user.username,
                privileges=mock_user.privileges
            )
            mock_get_user_by_token.return_value = mock_user_obj
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_info.return_value = mock_user_me
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/v1/auth/me",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == mock_user.username
            assert "valid_until" in data

    async def test_me_missing_token(
        self,
        app,
        mock_metrics,
    ):
        """Test me endpoint fails when authorization token is missing."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/auth/me")
            
            assert response.status_code == 401

    async def test_me_invalid_token(
        self,
        app,
        mock_metrics,
    ):
        """Test me endpoint fails with invalid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token"}
            )
            
            assert response.status_code == 401

    async def test_me_user_not_found(
        self,
        app,
        valid_token,
        mock_metrics,
    ):
        """Test me endpoint fails when user does not exist."""
        from domain.auth import UserDoesNotExists
        
        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.get_user_info") as mock_get_info:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)
            
            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = None  # User not found
            mock_get_info.side_effect = UserDoesNotExists
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/v1/auth/me",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            
            assert response.status_code == 401


    async def test_me_user_not_found_service_error(
        self,
        app,
        mock_user,
        valid_token,
        mock_metrics,
    ):
        """Test me endpoint returns 404 when service reports missing user."""
        from domain.auth import UserDoesNotExists

        with patch("services.database.get_db") as mock_get_db, \
             patch("repository.auth.AuthRepository.get_user_by_token") as mock_get_user, \
             patch("api.v1.auth.get_user_info") as mock_get_info:
            
            async def mock_get_db_impl():
                yield MagicMock(spec=AsyncSession)

            mock_get_db.return_value = mock_get_db_impl()
            mock_get_user.return_value = MagicMock(
                id=mock_user.id,
                username=mock_user.username,
                privileges=mock_user.privileges,
            )
            mock_get_info.side_effect = UserDoesNotExists

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/v1/auth/me",
                    headers={"Authorization": f"Bearer {valid_token}"}
                )

            assert response.status_code == 404
