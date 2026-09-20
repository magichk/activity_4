from fastapi import APIRouter, Depends, Header, UploadFile

from app.files.api.schemas import (
    FileCreatedResponse,
    FileDetail,
    FileMetadataRequest,
    FileSummary,
    MergeRequest,
    MessageResponse,
)
from app.files.dependency_injection.container import get_file_service
from app.files.domain.services import FileService, FileView

router = APIRouter(prefix="/files", tags=["files"])

AUTH_HEADER = Header(alias="Auth", description="Token de sesion devuelto por el login")
UNAUTHORIZED = {"model": MessageResponse, "description": "Token de sesion no valido"}
NOT_FOUND = {"model": MessageResponse, "description": "El fichero no existe"}


def to_summary(view: FileView) -> FileSummary:
    return FileSummary(
        id=view.file.id,
        owner_id=view.file.owner_id,
        name=view.file.name,
        description=view.file.description,
        has_content=view.has_content,
    )


@router.get(
    "",
    response_model=list[FileSummary],
    summary="Listar los ficheros del usuario",
    responses={401: UNAUTHORIZED},
)
async def list_files(auth: str = AUTH_HEADER, service: FileService = Depends(get_file_service)):
    return [to_summary(stored) for stored in await service.list_files(auth)]


@router.post(
    "",
    response_model=FileCreatedResponse,
    summary="Crear un fichero con su informacion",
    responses={401: UNAUTHORIZED},
)
async def create_file(
    payload: FileMetadataRequest,
    auth: str = AUTH_HEADER,
    service: FileService = Depends(get_file_service),
):
    """Registra los metadatos del fichero. El contenido se sube despues contra POST /files/{id}."""
    file_id = await service.create(auth, payload.name, payload.description)
    return FileCreatedResponse(id=file_id)


@router.post(
    "/merge",
    response_model=FileCreatedResponse,
    summary="Fusionar varios PDFs en uno nuevo",
    responses={
        400: {"model": MessageResponse, "description": "Falta contenido o el PDF no es valido"},
        401: UNAUTHORIZED,
        404: NOT_FOUND,
    },
)
async def merge_files(
    payload: MergeRequest,
    auth: str = AUTH_HEADER,
    service: FileService = Depends(get_file_service),
):
    """Une el contenido de los PDFs indicados y guarda el resultado como un fichero nuevo."""
    merged_id = await service.merge(auth, payload.file_ids, payload.name)
    return FileCreatedResponse(id=merged_id)


@router.get(
    "/{file_id}",
    response_model=FileDetail,
    summary="Consultar un fichero y su enlace de descarga",
    responses={401: UNAUTHORIZED, 404: NOT_FOUND},
)
async def get_file(
    file_id: int, auth: str = AUTH_HEADER, service: FileService = Depends(get_file_service)
):
    """Devuelve los metadatos y, si hay contenido, una URL firmada para descargarlo
    directamente de S3 en vez de hacerla pasar por este servidor."""
    view = await service.get(auth, file_id)
    detail = FileDetail(**to_summary(view).model_dump())
    if view.has_content:
        detail.download_url = await service.download_url(auth, file_id)
    return detail


@router.post(
    "/{file_id}",
    response_model=MessageResponse,
    summary="Subir el contenido de un fichero",
    responses={401: UNAUTHORIZED, 404: NOT_FOUND},
)
async def upload_content(
    file_id: int,
    upload: UploadFile,
    auth: str = AUTH_HEADER,
    service: FileService = Depends(get_file_service),
):
    await service.set_content(auth, file_id, await upload.read())
    return MessageResponse(detail=f"Contenido guardado para el fichero {file_id}")


@router.delete(
    "/{file_id}",
    response_model=MessageResponse,
    summary="Borrar un fichero",
    responses={401: UNAUTHORIZED, 404: NOT_FOUND},
)
async def delete_file(
    file_id: int, auth: str = AUTH_HEADER, service: FileService = Depends(get_file_service)
):
    await service.delete(auth, file_id)
    return MessageResponse(detail=f"Fichero {file_id} borrado")
