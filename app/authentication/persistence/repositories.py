import secrets

from tortoise.exceptions import IntegrityError

from app.authentication.domain.entities import User
from app.authentication.domain.ports import SessionRepository, UserRepository
from app.authentication.models import Session as SessionModel
from app.authentication.models import User as UserModel

EXTERNAL_ID_RANGE = 1_000_000_000
EXTERNAL_ID_ATTEMPTS = 5


def to_entity(row: UserModel) -> User:
    return User(external_id=row.external_id, email=row.email, name=row.name)


class TortoiseUserRepository(UserRepository):
    """Implementacion del puerto de usuarios contra Postgres."""

    async def exists(self, email: str) -> bool:
        return await UserModel.filter(email=email).exists()

    async def create(self, email: str, password_hash: str, name: str | None) -> User:
        for _ in range(EXTERNAL_ID_ATTEMPTS):
            try:
                row = await UserModel.create(
                    external_id=secrets.randbelow(EXTERNAL_ID_RANGE) + 1,
                    email=email,
                    password_hash=password_hash,
                    name=name,
                )
            except IntegrityError:
                # Solo se reintenta si el choque ha sido con el identificador externo.
                if await UserModel.filter(email=email).exists():
                    raise
                continue
            return to_entity(row)
        raise RuntimeError("No se ha podido asignar un identificador externo libre")

    async def find_with_password(self, email: str) -> tuple[User, str] | None:
        row = await UserModel.get_or_none(email=email)
        return None if row is None else (to_entity(row), row.password_hash)

    async def get_by_external_id(self, external_id: int) -> User | None:
        row = await UserModel.get_or_none(external_id=external_id)
        return None if row is None else to_entity(row)


class TortoiseSessionRepository(SessionRepository):
    """Implementacion del puerto de sesiones contra Postgres.

    Ya no la usa el contenedor de inyeccion de dependencias (ese papel lo hace ahora
    RedisSessionRepository), pero se deja funcionando tal cual para demostrar que el
    puerto SessionRepository es realmente intercambiable: basta con cambiar una linea en
    dependency_injection/container.py para volver a Postgres sin tocar el dominio ni la API.
    """

    async def create(self, token: str, external_id: int) -> None:
        user = await UserModel.get(external_id=external_id)
        await SessionModel.create(token=token, user=user)

    async def get_external_id(self, token: str) -> int | None:
        row = await SessionModel.get_or_none(token=token).prefetch_related("user")
        return None if row is None else row.user.external_id

    async def delete(self, token: str) -> bool:
        return await SessionModel.filter(token=token).delete() > 0
