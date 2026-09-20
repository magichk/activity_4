from functools import lru_cache

from app.authentication.dependency_injection.container import get_authentication_service
from app.files.domain.services import FileService
from app.files.persistence.identity import AuthenticationUserResolver
from app.files.persistence.pdf import PypdfMerger
from app.files.persistence.repositories import TortoiseFileRepository
from app.files.persistence.s3_storage import S3FileContentStore


@lru_cache(maxsize=1)
def get_content_store() -> S3FileContentStore:
    """Singleton del adaptador de S3, para no abrir un cliente boto3 nuevo por peticion."""
    return S3FileContentStore()


@lru_cache(maxsize=1)
def get_file_service() -> FileService:
    """Singleton que enlaza la API con el dominio de ficheros."""
    return FileService(
        files=TortoiseFileRepository(),
        content=get_content_store(),
        merger=PypdfMerger(),
        users=AuthenticationUserResolver(get_authentication_service()),
    )
