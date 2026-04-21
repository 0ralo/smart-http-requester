import psycopg
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from core import hash_password
from core.auth import check_password
from repository import AuthRepository
from schemas import UserRegisterBody, UserLoginBody, UserRegisterResponse, AccessTokenResponse


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
    user_password = await repo.get_user(data.username)
    if user_password is None:
        raise UserDoesNotExists
    password_correct = check_password(data.password_hash, user_password)
    if not password_correct:
        raise PasswordIsIncorrect
    return AccessTokenResponse(token_type="Bearer", access_token="TEMPORARY TOKEN")
