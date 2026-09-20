from functools import lru_cache

from redis.asyncio import Redis, from_url

from app.authentication.domain.security import Pbkdf2PasswordHasher, UrlSafeTokenGenerator
from app.authentication.domain.services import AuthenticationService
from app.authentication.persistence.redis_repository import RedisSessionRepository
from app.authentication.persistence.repositories import TortoiseUserRepository
from app.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Un unico cliente Redis por proceso, reutilizado por todas las peticiones."""
    return from_url(settings.redis_url, decode_responses=True)


@lru_cache(maxsize=1)
def get_authentication_service() -> AuthenticationService:
    """Singleton que enlaza la API con el dominio de autenticacion.

    Las sesiones van a Redis, no a Postgres: TortoiseSessionRepository sigue disponible en
    persistence/repositories.py y cumple exactamente el mismo puerto, asi que volver a
    Postgres seria cambiar la linea de abajo, nada mas.
    """
    return AuthenticationService(
        users=TortoiseUserRepository(),
        sessions=RedisSessionRepository(get_redis_client(), settings.session_ttl_seconds),
        hasher=Pbkdf2PasswordHasher(),
        tokens=UrlSafeTokenGenerator(),
    )
