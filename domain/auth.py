import uuid

import psycopg
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from core import hash_password
from core.auth import check_password
from repository import AuthRepository
from schemas import UserRegisterBody, UserLoginBody, UserRegisterResponse, AccessTokenResponse, UserMe


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
    hashed = hash_password(data.password_hash)
    repo = AuthRepository(session)
    try:
        return await repo.create_new_user(data.username, hashed)
    except sqlalchemy.exc.IntegrityError as e:
        match type(e.orig):
            case psycopg.errors.UniqueViolation:
                raise UserAlreadyExists
            case _:
                raise UnknownException


async def get_token(
    session: AsyncSession,
    data: UserLoginBody
):
    repo = AuthRepository(session)
    id_with_hash = await repo.get_user_id_password(data.username)
    if id_with_hash.user_id is None:
        raise UserDoesNotExists
    password_correct = check_password(data.password_hash, id_with_hash.password_hash)
    if not password_correct:
        raise PasswordIsIncorrect
    token = await repo.get_access_token_by_user_id(id_with_hash.user_id)
    return AccessTokenResponse(token_type="Bearer", access_token=str(token))


async def delete_token(
    session: AsyncSession,
    user_id: int
) -> int:
    repo = AuthRepository(session)
    deleted_id = await repo.delete_token(user_id)
    if deleted_id is None:
        raise UserDoesNotExists
    return deleted_id


async def refresh_token(
    session: AsyncSession,
    user_id: int
) -> AccessTokenResponse:
    repo = AuthRepository(session)
    token = await repo.refresh_user_token(user_id)
    if token is None:
        raise UserDoesNotExists
    return AccessTokenResponse(access_token=str(token), token_type="Bearer")


async def get_user_info(
    session: AsyncSession,
    user_id: int
) -> UserMe:
    repo = AuthRepository(session)
    info = await repo.get_user_info(user_id)
    if info is None:
        raise UserDoesNotExists
    return UserMe.model_validate(info)

