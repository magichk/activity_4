import hashlib
import hmac
import os
import secrets

from app.authentication.domain.ports import PasswordHasher, TokenGenerator

PBKDF2_ITERATIONS = 200_000


class Pbkdf2PasswordHasher(PasswordHasher):
    """Guarda la contrasena como salt$hash usando PBKDF2-HMAC-SHA256."""

    def __init__(self, iterations: int = PBKDF2_ITERATIONS):
        self._iterations = iterations

    def hash(self, password: str) -> str:
        salt = os.urandom(16)
        return f"{salt.hex()}${self._digest(password, salt)}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            salt_hex, digest_hex = stored.split("$")
        except ValueError:
            return False
        candidate = self._digest(password, bytes.fromhex(salt_hex))
        return hmac.compare_digest(candidate, digest_hex)

    def _digest(self, password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self._iterations).hex()


class UrlSafeTokenGenerator(TokenGenerator):
    def __init__(self, bytes_length: int = 32):
        self._bytes_length = bytes_length

    def generate(self) -> str:
        return secrets.token_urlsafe(self._bytes_length)
