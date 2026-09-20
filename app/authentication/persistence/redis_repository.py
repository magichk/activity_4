from redis.asyncio import Redis

from app.authentication.domain.ports import SessionRepository

SESSION_KEY_PREFIX = "session:"


class RedisSessionRepository(SessionRepository):
    """Implementacion del puerto de sesiones contra Redis.

    El valor guardado es solo el external_id como texto: Redis actua de cache/puntero,
    nunca de fuente de verdad del perfil del usuario (eso lo sigue teniendo Postgres via
    UserRepository). El TTL lo pone Redis mismo con EX, no un campo "expires_at" que
    alguien tendria que revisar a mano.
    """

    def __init__(self, client: Redis, ttl_seconds: int):
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def create(self, token: str, external_id: int) -> None:
        await self._client.set(self._key(token), str(external_id), ex=self._ttl_seconds)

    async def get_external_id(self, token: str) -> int | None:
        value = await self._client.get(self._key(token))
        return None if value is None else int(value)

    async def delete(self, token: str) -> bool:
        deleted = await self._client.delete(self._key(token))
        return deleted > 0

    @staticmethod
    def _key(token: str) -> str:
        return f"{SESSION_KEY_PREFIX}{token}"
