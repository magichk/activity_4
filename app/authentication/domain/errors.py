class AuthenticationError(Exception):
    """Error de negocio del modulo de autenticacion."""


class EmailAlreadyRegistered(AuthenticationError):
    def __init__(self, email: str):
        super().__init__(f"El correo {email} ya esta registrado")


class InvalidCredentials(AuthenticationError):
    def __init__(self):
        super().__init__("Credenciales incorrectas")


class InvalidSession(AuthenticationError):
    def __init__(self):
        super().__init__("Token de sesion no valido")
