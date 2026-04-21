from pydantic import BaseModel, field_validator


class UserCredentials(BaseModel):
    username: str
    password_hash: str

    @field_validator("password_hash")
    def password_hash_validator(cls, value: str):
        if len(value) != 64:  # HEX of sha256
            raise ValueError("Password hash must be 64 characters long")
        return value


class UserRegisterBody(UserCredentials):
    ...


class UserLoginBody(UserRegisterBody):
    ...



class UserRegisterResponse(BaseModel):
    user_id: int
    username: str

    class Config:
        from_attributes = True


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
