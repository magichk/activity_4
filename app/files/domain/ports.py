from abc import ABC, abstractmethod

from app.files.domain.entities import StoredFile


class FileRepository(ABC):
    """Puerto de salida hacia los metadatos del fichero (Postgres).

    El contenido no es responsabilidad suya: eso lo cubre FileContentStore.
    """

    @abstractmethod
    async def create(self, owner_id: int, name: str, description: str | None) -> int: ...

    @abstractmethod
    async def list_for_owner(self, owner_id: int) -> list[StoredFile]: ...

    @abstractmethod
    async def get_for_owner(self, file_id: int, owner_id: int) -> StoredFile | None: ...

    @abstractmethod
    async def delete(self, file_id: int) -> bool: ...


class FileContentStore(ABC):
    """Puerto de salida hacia el almacen de objetos (S3 / MinIO) que guarda los bytes.

    Separado de FileRepository a proposito: son dos infraestructuras distintas (una base de
    datos relacional para los metadatos, un object storage para el contenido), cada una con
    su propio adaptador e implementacion, tal y como pide la actividad.
    """

    @abstractmethod
    async def put(self, file_id: int, content: bytes) -> None: ...

    @abstractmethod
    async def get(self, file_id: int) -> bytes | None: ...

    @abstractmethod
    async def exists(self, file_id: int) -> bool: ...

    @abstractmethod
    async def delete(self, file_id: int) -> None: ...

    @abstractmethod
    async def presigned_download_url(self, file_id: int) -> str | None:
        """URL firmada y temporal para descargar el fichero directamente desde S3.

        Es la razon de ser de usar S3: el contenido no pasa por nuestro servidor.
        """


class PdfMerger(ABC):
    """Puerto de salida hacia la herramienta que fusiona PDFs."""

    @abstractmethod
    def merge(self, documents: list[bytes]) -> bytes: ...


class UserResolver(ABC):
    """Puerto de entrada al modulo de autenticacion.

    Ficheros solo necesita saber a que usuario pertenece un token, no como se gestionan
    las sesiones, asi que depende de esta abstraccion y no del servicio de autenticacion.
    """

    @abstractmethod
    async def external_id_for(self, token: str) -> int: ...
