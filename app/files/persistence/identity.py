from app.authentication.domain.services import AuthenticationService
from app.files.domain.ports import UserResolver


class AuthenticationUserResolver(UserResolver):
    """Adaptador que resuelve el token contra el modulo de autenticacion."""

    def __init__(self, authentication: AuthenticationService):
        self._authentication = authentication

    async def external_id_for(self, token: str) -> int:
        user = await self._authentication.introspect(token)
        return user.external_id
