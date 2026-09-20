from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="Correo que identifica al usuario")
    password: str = Field(min_length=8, description="Contrasena en claro")
    name: str | None = Field(default=None, description="Nombre visible del usuario")


class RegisterResponse(BaseModel):
    external_id: int
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str = Field(description="Token de sesion a enviar en la cabecera Auth")


class IntrospectResponse(BaseModel):
    active: bool
    external_id: int
    email: EmailStr
    name: str | None = None


class MessageResponse(BaseModel):
    detail: str
