"""
Password hashing and verification using Argon2.
"""
import logging
from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHash,
)

logger = logging.getLogger(__name__)

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=16,
    salt_len=16,
)


class PasswordService:
    """Password hashing and verification service using Argon2."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using Argon2."""
        try:
            return _hasher.hash(password)
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise
    
    @staticmethod
    def verify_password(password: str, hash_: str) -> bool:
        """Verify a password against its hash."""
        try:
            _hasher.verify(hash_, password)
            return True
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHash) as e:
            logger.warning(f"Password verification error: {e}")
            return False
