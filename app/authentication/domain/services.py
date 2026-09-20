from app.authentication.domain.entities import Credentials, User
from app.authentication.domain.errors import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidSession,
)
from app.authentication.domain.ports import (
    PasswordHasher,
    SessionRepository,
    TokenGenerator,
    UserRepository,
)


class AuthenticationService:
    """Logica de registro y de sesiones.

    Trabaja siempre contra los puertos, de modo que cambiar Postgres por otro almacen no
    obliga a tocar nada de este fichero.
    """

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        tokens: TokenGenerator,
    ):
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._tokens = tokens

    async def register(self, credentials: Credentials, name: str | None = None) -> User:
        if await self._users.exists(credentials.email):
            raise EmailAlreadyRegistered(credentials.email)
        return await self._users.create(
            email=credentials.email,
            password_hash=self._hasher.hash(credentials.password),
            name=name,
        )

    async def login(self, credentials: Credentials) -> str:
        found = await self._users.find_with_password(credentials.email)
        if found is None:
            raise InvalidCredentials()

        user, password_hash = found
        if not self._hasher.verify(credentials.password, password_hash):
            raise InvalidCredentials()

        token = self._tokens.generate()
        await self._sessions.create(token, user.external_id)
        return token

    async def logout(self, token: str) -> None:
        if not await self._sessions.delete(token):
            raise InvalidSession()

    async def introspect(self, token: str) -> User:
        external_id = await self._sessions.get_external_id(token)
        if external_id is None:
            raise InvalidSession()

        user = await self._users.get_by_external_id(external_id)
        if user is None:
            # La sesion es valida pero el usuario ya no existe: se trata igual que un
            # token invalido en vez de devolver un 500.
            raise InvalidSession()
        return user
