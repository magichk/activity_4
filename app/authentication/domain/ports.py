from abc import ABC, abstractmethod

from app.authentication.domain.entities import User


class UserRepository(ABC):
    """Puerto de salida hacia el almacen de usuarios."""

    @abstractmethod
    async def exists(self, email: str) -> bool: ...

    @abstractmethod
    async def create(self, email: str, password_hash: str, name: str | None) -> User: ...

    @abstractmethod
    async def find_with_password(self, email: str) -> tuple[User, str] | None:
        """Devuelve el usuario y el hash de su contrasena, o None si no existe."""

    @abstractmethod
    async def get_by_external_id(self, external_id: int) -> User | None: ...


class SessionRepository(ABC):
    """Puerto de salida hacia el almacen de sesiones.

    Guarda solo el puntero token -> external_id, nunca el perfil del usuario: quien conoce
    el email y el nombre es UserRepository. Asi el adaptador de sesiones (Postgres o Redis,
    ahora mismo Redis) no necesita saber nada del resto de columnas de "users" ni romperse
    cuando ese modelo cambie.
    """

    @abstractmethod
    async def create(self, token: str, external_id: int) -> None: ...

    @abstractmethod
    async def get_external_id(self, token: str) -> int | None: ...

    @abstractmethod
    async def delete(self, token: str) -> bool: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, stored: str) -> bool: ...


class TokenGenerator(ABC):
    @abstractmethod
    def generate(self) -> str: ...
