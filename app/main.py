from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tortoise import Tortoise

from app.authentication.api.router import router as authentication_router
from app.authentication.dependency_injection.container import get_redis_client
from app.authentication.domain.errors import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidSession,
)
from app.config import settings
from app.db import TORTOISE_ORM
from app.files.api.router import router as files_router
from app.files.dependency_injection.container import get_content_store
from app.files.domain.errors import (
    FileNotFound,
    FileWithoutContent,
    InvalidPdf,
    NotEnoughFilesToMerge,
)

# El dominio no conoce HTTP: cada error de negocio se traduce aqui a su codigo de respuesta.
ERROR_STATUS = {
    EmailAlreadyRegistered: 409,
    InvalidCredentials: 401,
    InvalidSession: 401,
    FileNotFound: 404,
    FileWithoutContent: 400,
    InvalidPdf: 400,
    NotEnoughFilesToMerge: 400,
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    if settings.generate_schemas:
        await Tortoise.generate_schemas(safe=True)
    await get_content_store().ensure_bucket()
    yield
    await get_redis_client().aclose()
    await Tortoise.close_connections()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(authentication_router)
app.include_router(files_router)


def domain_error_handler(status_code: int):
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


for error, code in ERROR_STATUS.items():
    app.add_exception_handler(error, domain_error_handler(code))


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": settings.app_version}
