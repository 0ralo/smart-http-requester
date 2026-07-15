import hashlib
import uuid

import asyncpg
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from core import hash_password
from core.auth import check_password
from repository import AuthRepository
from schemas import UserRegisterBody, UserLoginBody, UserRegisterResponse, AccessTokenResponse, UserMe
from services.logger import logger


class UserAlreadyExists(Exception):
    pass

class UnknownException(Exception):
    pass

class UserDoesNotExists(Exception):
    pass

class PasswordIsIncorrect(Exception):
    pass

async def create_user(
    session: AsyncSession,
    data: UserRegisterBody
) -> UserRegisterResponse:
    logger.info("Creating user with username=%s", data.username)
    hashed = hash_password(data.password_hash)
    repo = AuthRepository(session)
    try:
        user = await repo.create_new_user(data.username, hashed)
        logger.info("User created successfully: username=%s user_id=%s", data.username, user.user_id)
        return user
    except sqlalchemy.exc.IntegrityError as e:
        unique_violation_types = tuple(
            cls for cls in (
                getattr(asyncpg.exceptions, "UniqueViolation", None),
                getattr(asyncpg.exceptions, "UniqueViolationError", None),
            )
            if cls is not None
        )
        if unique_violation_types and isinstance(e.orig, unique_violation_types):
            logger.warning("User creation failed: username already exists (%s)", data.username)
            raise UserAlreadyExists
        logger.exception("Unexpected database error while creating user %s", data.username)
        raise UnknownException


async def get_token(
    session: AsyncSession,
    data: UserLoginBody
) -> AccessTokenResponse:
    repo = AuthRepository(session)
    logger.debug("Generating token for username=%s", data.username)
    id_with_hash = await repo.get_user_id_password(data.username)
    if id_with_hash is None:
        logger.warning("Token generation failed: username not found (%s)", data.username)
        raise UserDoesNotExists
    password_correct = check_password(data.password_hash, id_with_hash.password_hash)
    if not password_correct:
        logger.warning("Token generation failed: invalid password for username=%s", data.username)
        raise PasswordIsIncorrect
    token = await repo.get_access_token_by_user_id(id_with_hash.user_id)
    logger.info("Token generated successfully for username=%s user_id=%s", data.username, id_with_hash.user_id)
    return AccessTokenResponse(access_token=str(token))


async def get_token_for_docs(
    session: AsyncSession,
    login: str,
    password: str
) -> AccessTokenResponse:
    repo = AuthRepository(session)
    logger.debug("Generating docs token for username=%s", login)
    id_with_hash = await repo.get_user_id_password(login)
    if id_with_hash is None:
        logger.warning("Docs token generation failed: username not found (%s)", login)
        raise UserDoesNotExists
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    password_correct = check_password(password_hash, id_with_hash.password_hash)
    if not password_correct:
        logger.warning("Docs token generation failed: invalid password for username=%s", login)
        raise PasswordIsIncorrect
    token = await repo.get_access_token_by_user_id(id_with_hash.user_id)
    logger.info("Docs token generated successfully for username=%s user_id=%s", login, id_with_hash.user_id)
    return AccessTokenResponse(access_token=str(token))


async def delete_token(
    session: AsyncSession,
    user_id: int
) -> int:
    repo = AuthRepository(session)
    logger.info("Deleting token for user_id=%s", user_id)
    deleted_id = await repo.delete_token(user_id)
    if deleted_id is None:
        logger.warning("Token deletion failed: user_id=%s not found", user_id)
        raise UserDoesNotExists
    logger.info("Token deleted successfully for user_id=%s", user_id)
    return deleted_id


async def refresh_token(
    session: AsyncSession,
    user_id: int
) -> AccessTokenResponse:
    repo = AuthRepository(session)
    logger.info("Refreshing token for user_id=%s", user_id)
    token = await repo.refresh_user_token(user_id)
    if token is None:
        logger.warning("Token refresh failed: user_id=%s not found", user_id)
        raise UserDoesNotExists
    logger.info("Token refreshed successfully for user_id=%s", user_id)
    return AccessTokenResponse(access_token=str(token), token_type="Bearer")


async def get_user_info(
    session: AsyncSession,
    user_id: int
) -> UserMe:
    repo = AuthRepository(session)
    logger.debug("Fetching user info for user_id=%s", user_id)
    info = await repo.get_user_info(user_id)
    if info is None:
        logger.warning("User info fetch failed: user_id=%s not found", user_id)
        raise UserDoesNotExists
    logger.debug("User info fetched for user_id=%s", user_id)
    return UserMe.model_validate(info)

