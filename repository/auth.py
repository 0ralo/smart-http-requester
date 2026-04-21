from sqlalchemy import text, BindParameter, TEXT, Integer
from sqlalchemy.dialects.postgresql import BYTEA

from schemas import UserRegisterResponse


class AuthRepository:

    def __init__(self, manager):
        self.manager = manager

    async def create_new_user(self, username: str, password: bytes, role_id: int = 1) -> UserRegisterResponse:
        async with self.manager as session:
            query = await session.execute(text("""
                    insert into users(username, password_hash, role_id)
                    values (:username, :password_hash, :role_id)
                    returning id as user_id, username
                """
            ).bindparams(
                BindParameter("username", username, TEXT),
                BindParameter("password_hash", password, BYTEA),
                BindParameter("role_id", role_id, Integer),
            ))
            await session.commit()
            raw_user = query.fetchone()
            return UserRegisterResponse.model_validate(raw_user)


    async def get_user(self, username: str) -> bytes:
        async with self.manager as session:
            query = await session.execute(text("""
                select password_hash from users where username = :username
            """).bindparams(BindParameter("username", username, TEXT)))
            return query.scalar_one_or_none()

