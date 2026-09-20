from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """Usuario tal y como lo entiende el dominio, sin detalles de persistencia."""

    external_id: int
    email: str
    name: str | None = None


@dataclass(frozen=True)
class Credentials:
    email: str
    password: str
