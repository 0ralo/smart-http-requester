import argon2
import bcrypt

from loguru import logger
from config import settings

if not settings.use_argon:

    def hash_password(password: str) -> bytes:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt)

    def check_password(password: str, hashed_password: bytes) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), hashed_password)
        except ValueError as e:
            logger.error(f"Invalid password error: {e}")
            return False
else:

    class ArgonConfig:
        ARGON2_TIME_COST = 3  # number of iterations
        ARGON2_MEMORY_COST = 65536  # 64 mb in kb used memory
        ARGON2_PARALLELISM = 4  # number of threads
        ARGON2_HASH_LEN = 32  # hash length
        ARGON2_SALT_LEN = 16  # salt length

    ph = argon2.PasswordHasher(
        time_cost=ArgonConfig.ARGON2_TIME_COST,
        memory_cost=ArgonConfig.ARGON2_MEMORY_COST,
        parallelism=ArgonConfig.ARGON2_PARALLELISM,
        hash_len=ArgonConfig.ARGON2_HASH_LEN,
        salt_len=ArgonConfig.ARGON2_SALT_LEN,
    )

    def hash_password(password: str) -> bytes:
        try:
            hash_str = ph.hash(password)
            return hash_str.encode()
        except argon2.exceptions.HashingError as e:
            logger.error(
                f"Hashing error: {e} for password={password[len(password) // 4 :]}{'*' * (len(password) // 4 * 3)}"
            )
            raise e

    def check_password(password, hashed_password: bytes):
        try:
            hash_str = hashed_password.decode("utf-8")
            ph.verify(hash_str, password)
            if ph.check_needs_rehash(hash_str):
                logger.info(f"Password rehash need for {password}")
                return True
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
        except argon2.exceptions.VerificationError as e:
            logger.error(f"Verification error: {e}")
            return False
        except argon2.exceptions.InvalidHashError as e:
            logger.error(f"Invalid hash error: {e}")
            return False
