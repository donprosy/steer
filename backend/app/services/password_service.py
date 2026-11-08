"""Argon2id password hashing and verification."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

password_hasher = PasswordHasher()


def hash_password(password):
    """Hash a plaintext password using the configured Argon2id parameters."""
    return password_hasher.hash(password)


def verify_password(password_hash, password):
    """Return whether a password matches, without exposing hash errors."""
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_hash_needs_rehash(password_hash):
    try:
        return password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True

