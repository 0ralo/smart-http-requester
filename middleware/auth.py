from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from repository import AuthRepository
from schemas import User
from services.database import async_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def is_str_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False

def authorization(privileges=0):
    async def wrapper(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
        if not is_str_uuid(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        repo = AuthRepository(async_session())
        user = await repo.get_user_by_token(token)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        if user.privileges < privileges:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return User.model_validate(user)
    return wrapper
