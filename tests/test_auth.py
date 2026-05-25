"""Tests for authentication endpoints."""
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport


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
