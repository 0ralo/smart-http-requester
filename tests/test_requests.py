"""Tests for /requests endpoints."""
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.tasks import AccessDeniedError, InvalidTaskStatusError, TaskNotFoundError
from schemas import TaskCreate, TaskResponse, TaskUpdate, User


def _mock_user_for_auth(user: User) -> MagicMock:
    return MagicMock(id=user.id, username=user.username, privileges=user.privileges)


@pytest.mark.asyncio
class TestRequestCreate:
    async def test_create_request_success(
        self,
        client,
        valid_token: str,
        mock_user: User,
        task_create_body: TaskCreate,
        mock_task_response: TaskResponse,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.create_request_task") as mock_create_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_create_request_task.return_value = mock_task_response

            response = await client.post(
                "/v1/requests/",
                json=task_create_body.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(mock_task_response.id)
            assert data["url"] == str(task_create_body.url)
            mock_create_request_task.assert_called_once()

    async def test_create_request_server_error(
        self,
        client,
        valid_token: str,
        mock_user: User,
        task_create_body: TaskCreate,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.create_request_task") as mock_create_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_create_request_task.side_effect = Exception("database failure")

            response = await client.post(
                "/v1/requests/",
                json=task_create_body.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 500

    async def test_create_request_validation_error(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)

            response = await client.post(
                "/v1/requests/",
                json={"method": "GET"},
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 422


@pytest.mark.asyncio
class TestRequestInfo:
    async def test_get_request_success(
        self,
        client,
        valid_token: str,
        mock_user: User,
        mock_task_response: TaskResponse,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.get_request_task") as mock_get_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_get_request_task.return_value = mock_task_response

            response = await client.get(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 200
            assert response.json()["id"] == str(mock_task_response.id)

    async def test_get_request_not_found(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.get_request_task") as mock_get_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_get_request_task.side_effect = TaskNotFoundError

            response = await client.get(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 404

    async def test_get_request_access_denied(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.get_request_task") as mock_get_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_get_request_task.side_effect = AccessDeniedError

            response = await client.get(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 403


@pytest.mark.asyncio
class TestRequestUserTasks:
    async def test_get_user_tasks_success(
        self,
        client,
        valid_token: str,
        mock_user: User,
        mock_task_response_list: list[TaskResponse],
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.get_user_request_tasks") as mock_get_user_tasks:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_get_user_tasks.return_value = mock_task_response_list

            response = await client.get(
                "/v1/requests/?skip=0&limit=20",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 200
            assert len(response.json()) == 1

    async def test_get_user_tasks_invalid_skip(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)

            response = await client.get(
                "/v1/requests/?skip=-1&limit=20",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 422


@pytest.mark.asyncio
class TestRequestDelete:
    async def test_delete_request_success(
        self,
        client,
        valid_token: str,
        mock_user: User,
        mock_task_response: TaskResponse,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.cancel_request_task") as mock_cancel_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_cancel_task.return_value = mock_task_response

            response = await client.delete(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == mock_task_response.status

    async def test_delete_request_not_found(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.cancel_request_task") as mock_cancel_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_cancel_task.side_effect = TaskNotFoundError

            response = await client.delete(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 404

    async def test_delete_request_access_denied(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.cancel_request_task") as mock_cancel_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_cancel_task.side_effect = AccessDeniedError

            response = await client.delete(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 403

    async def test_delete_request_invalid_status(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.cancel_request_task") as mock_cancel_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_cancel_task.side_effect = InvalidTaskStatusError("Task is not pending")

            response = await client.delete(
                f"/v1/requests/{task_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 400


@pytest.mark.asyncio
class TestRequestUpdate:
    async def test_update_request_success(
        self,
        client,
        valid_token: str,
        mock_user: User,
        task_update_body: TaskUpdate,
        mock_task_response: TaskResponse,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.update_request_task") as mock_update_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_update_request_task.return_value = mock_task_response

            response = await client.put(
                f"/v1/requests/{task_id}",
                json=task_update_body.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 200
            assert response.json()["id"] == str(mock_task_response.id)

    async def test_update_request_not_found(
        self,
        client,
        valid_token: str,
        mock_user: User,
        task_update_body: TaskUpdate,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.update_request_task") as mock_update_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_update_request_task.side_effect = TaskNotFoundError

            response = await client.put(
                f"/v1/requests/{task_id}",
                json=task_update_body.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 404

    async def test_update_request_access_denied(
        self,
        client,
        valid_token: str,
        mock_user: User,
        task_update_body: TaskUpdate,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.update_request_task") as mock_update_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_update_request_task.side_effect = AccessDeniedError

            response = await client.put(
                f"/v1/requests/{task_id}",
                json=task_update_body.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 403

    async def test_update_request_invalid_status(
        self,
        client,
        valid_token: str,
        mock_user: User,
        task_update_body: TaskUpdate,
    ):
        task_id = uuid4()
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.update_request_task") as mock_update_request_task:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_update_request_task.side_effect = InvalidTaskStatusError("Task is not pending")

            response = await client.put(
                f"/v1/requests/{task_id}",
                json=task_update_body.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 400


@pytest.mark.asyncio
class TestRequestBatch:
    async def test_create_tasks_batch_success(
        self,
        client,
        valid_token: str,
        mock_user: User,
        mock_task_response_list: list[TaskResponse],
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.create_request_tasks_batch") as mock_create_batch:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_create_batch.return_value = mock_task_response_list

            # Создаем данные для batch запроса
            batch_data = [
                {
                    "url": str(mock_task.url),
                    "method": mock_task.method,
                    "headers": mock_task.headers,
                    "body": mock_task.body,
                    "max_attempts": mock_task.max_attempts
                }
                for mock_task in mock_task_response_list
            ]

            response = await client.post(
                "/v1/requests/batch",
                json=batch_data,
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 200
            assert len(response.json()) == 1

    async def test_create_tasks_batch_validation_error(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)

            response = await client.post(
                "/v1/requests/batch",
                json=[{"method": "GET"}],
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 422

    async def test_create_tasks_batch_domain_error(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.create_request_tasks_batch") as mock_create_batch:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_create_batch.side_effect = ValueError("bad batch")

            response = await client.post(
                "/v1/requests/batch",
                json=[{"url": "https://example.com", "method": "GET", "max_attempts": 1}],
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 400

    async def test_create_tasks_batch_server_error(
        self,
        client,
        valid_token: str,
        mock_user: User,
    ):
        with patch("api.v1.requests.get_db") as mock_get_db, \
             patch("middleware.auth.get_db") as mock_auth_get_db, \
             patch("middleware.auth.AuthRepository.get_user_by_token") as mock_get_user_by_token, \
             patch("api.v1.requests.create_request_tasks_batch") as mock_create_batch:

            mock_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_auth_get_db.return_value = AsyncMock(spec=AsyncSession)
            mock_get_user_by_token.return_value = _mock_user_for_auth(mock_user)
            mock_create_batch.side_effect = Exception("unexpected")

            response = await client.post(
                "/v1/requests/batch",
                json=[{"url": "https://example.com", "method": "GET", "max_attempts": 1}],
                headers={"Authorization": f"Bearer {valid_token}"},
            )

            assert response.status_code == 500