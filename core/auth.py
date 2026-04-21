import hashlib

import bcrypt


def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt(rounds=8)
    return bcrypt.hashpw(password.encode(), salt)


def check_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password)

