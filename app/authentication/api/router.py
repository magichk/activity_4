from fastapi import APIRouter, Depends, Header

from app.authentication.api.schemas import (
    IntrospectResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.authentication.dependency_injection.container import get_authentication_service
from app.authentication.domain.entities import Credentials
from app.authentication.domain.services import AuthenticationService

router = APIRouter(prefix="/authentication", tags=["authentication"])

AUTH_HEADER = Header(alias="Auth", description="Token de sesion devuelto por el login")
UNAUTHORIZED = {"model": MessageResponse, "description": "Token de sesion no valido"}


@router.post(
    "/register",
    response_model=RegisterResponse,
    summary="Registrar un usuario nuevo",
    responses={409: {"model": MessageResponse, "description": "El correo ya esta registrado"}},
)
async def register(
    payload: RegisterRequest,
    service: AuthenticationService = Depends(get_authentication_service),
):
    """Da de alta al usuario y le asigna un identificador externo entero y unico."""
    user = await service.register(
        Credentials(email=payload.email, password=payload.password), name=payload.name
    )
    return RegisterResponse(external_id=user.external_id, email=user.email)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Abrir una sesion",
    responses={401: {"model": MessageResponse, "description": "Credenciales incorrectas"}},
)
async def login(
    payload: LoginRequest,
    service: AuthenticationService = Depends(get_authentication_service),
):
    token = await service.login(Credentials(email=payload.email, password=payload.password))
    return LoginResponse(token=token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Cerrar la sesion asociada al token",
    responses={401: UNAUTHORIZED},
)
async def logout(
    auth: str = AUTH_HEADER,
    service: AuthenticationService = Depends(get_authentication_service),
):
    await service.logout(auth)
    return MessageResponse(detail="Sesion cerrada")


@router.get(
    "/introspect",
    response_model=IntrospectResponse,
    summary="Validar un token y devolver el usuario asociado",
    responses={401: UNAUTHORIZED},
)
async def introspect(
    auth: str = AUTH_HEADER,
    service: AuthenticationService = Depends(get_authentication_service),
):
    user = await service.introspect(auth)
    return IntrospectResponse(
        active=True, external_id=user.external_id, email=user.email, name=user.name
    )
