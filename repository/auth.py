import uuid
from typing import Optional

from sqlalchemy import text, BindParameter, TEXT, Integer, Uuid
from sqlalchemy.dialects.postgresql import BYTEA

from schemas import UserRegisterResponse, UserIdPassword, User, UserMe


class AuthRepository:

    def __init__(self, manager):
        self.manager = manager

    async def create_new_user(self, username: str, password: bytes, role_id: int = 1) -> UserRegisterResponse:
        async with self.manager as session:
            query = await session.execute(text("""
                    insert into users(username, password_hash, role_id)
                    values (:username, :password_hash, :role_id)
                    returning id as user_id, username
            """).bindparams(
                BindParameter("username", username, TEXT),
                BindParameter("password_hash", password, BYTEA),
                BindParameter("role_id", role_id, Integer),
            ))
            await session.commit()
            raw_user = query.fetchone()
            return UserRegisterResponse.model_validate(raw_user)


    async def get_user_id_password(self, username: str) -> UserIdPassword:
        async with self.manager as session:
            query = await session.execute(text("""
                select id as user_id, password_hash from users where username = :username
            """).bindparams(BindParameter("username", username, TEXT)))
            raw_data = query.fetchone()
            return UserIdPassword.model_validate(raw_data)


    async def get_access_token_by_user_id(self, user_id) -> uuid.UUID:
        async with self.manager as session:
            query = await session.execute(text("""
                select get_or_create_user_token(:user_id);
            """).bindparams(
                BindParameter("user_id", user_id, Integer))
            )
            await session.commit()
            return query.scalar_one()


    async def delete_token(self, user_id) -> Optional[int]:
        async with self.manager as session:
            query = await session.execute(text("""
                delete from tokens
                where user_id = :user_id
                returning user_id
            """).bindparams(
                BindParameter("user_id", user_id, Integer))
            )
            await session.commit()
            return query.scalar_one_or_none()


    async def get_user_by_token(self, token) -> User:
        async with self.manager as session:
            query = await session.execute(text("""
                select u.id, u.username, r.permissions as privileges
                from users u
                left join public.tokens t
                    on u.id = t.user_id
                left join public.roles r
                    on r.id = u.role_id
                where t.access_token = :access_token
            """).bindparams(
                BindParameter("access_token", token, Uuid))
            )
            return query.fetchone()

    async def refresh_user_token(self, user_id: int) -> uuid.UUID:
        async with self.manager as session:
            query = await session.execute(text("""
                update public.tokens
                set access_token = gen_random_uuid(),
                valid_until = now() + interval '7d'
                where user_id = :user_id
                returning access_token
                """).bindparams(
                    BindParameter("user_id", user_id, Integer)
            ))
            await session.commit()
            return query.scalar_one_or_none()

    async def get_user_info(self, user_id) -> UserMe:
        async with self.manager as session:
            query = await session.execute(text("""
                select
                u.username,
                t.valid_until
                from users u
                left join tokens t
                on u.id = t.user_id
                where u.id = :user_id
                """).bindparams(
                    BindParameter("user_id", user_id, Integer)
            ))
            return query.fetchone()
