from dataclasses import dataclass

from app.files.domain.entities import StoredFile
from app.files.domain.errors import FileNotFound, FileWithoutContent, NotEnoughFilesToMerge
from app.files.domain.ports import FileContentStore, FileRepository, PdfMerger, UserResolver

MINIMUM_FILES_TO_MERGE = 2


@dataclass(frozen=True)
class FileView:
    """Lo que necesita la API para responder: metadatos mas si hay contenido o no."""

    file: StoredFile
    has_content: bool


class FileService:
    """Logica de gestion de ficheros.

    Todas las operaciones parten del token: se resuelve el propietario y a partir de ahi
    ningun fichero de otro usuario es alcanzable. Los metadatos y el contenido viven en dos
    infraestructuras distintas (FileRepository contra Postgres, FileContentStore contra S3)
    y este servicio es el unico sitio que conoce a las dos a la vez.
    """

    def __init__(
        self,
        files: FileRepository,
        content: FileContentStore,
        merger: PdfMerger,
        users: UserResolver,
    ):
        self._files = files
        self._content = content
        self._merger = merger
        self._users = users

    async def list_files(self, token: str) -> list[FileView]:
        owner_id = await self._users.external_id_for(token)
        stored = await self._files.list_for_owner(owner_id)
        return [FileView(file, await self._content.exists(file.id)) for file in stored]

    async def create(self, token: str, name: str, description: str | None) -> int:
        owner_id = await self._users.external_id_for(token)
        return await self._files.create(owner_id, name, description)

    async def get(self, token: str, file_id: int) -> FileView:
        owner_id = await self._users.external_id_for(token)
        stored = await self._owned(file_id, owner_id)
        return FileView(stored, await self._content.exists(file_id))

    async def download_url(self, token: str, file_id: int) -> str | None:
        owner_id = await self._users.external_id_for(token)
        await self._owned(file_id, owner_id)
        return await self._content.presigned_download_url(file_id)

    async def set_content(self, token: str, file_id: int, content: bytes) -> None:
        owner_id = await self._users.external_id_for(token)
        await self._owned(file_id, owner_id)
        await self._content.put(file_id, content)

    async def delete(self, token: str, file_id: int) -> None:
        owner_id = await self._users.external_id_for(token)
        await self._owned(file_id, owner_id)
        await self._files.delete(file_id)
        await self._content.delete(file_id)

    async def merge(self, token: str, file_ids: list[int], name: str | None) -> int:
        if len(file_ids) < MINIMUM_FILES_TO_MERGE:
            raise NotEnoughFilesToMerge()

        owner_id = await self._users.external_id_for(token)
        sources = [await self._owned(file_id, owner_id) for file_id in file_ids]

        contents = []
        for source in sources:
            data = await self._content.get(source.id)
            if data is None:
                raise FileWithoutContent(source.id)
            contents.append(data)

        merged = self._merger.merge(contents)
        merged_id = await self._files.create(
            owner_id,
            name or "-".join(source.name.removesuffix(".pdf") for source in sources) + ".pdf",
            "Fusion de los ficheros " + ", ".join(str(source.id) for source in sources),
        )
        await self._content.put(merged_id, merged)
        return merged_id

    async def _owned(self, file_id: int, owner_id: int) -> StoredFile:
        """Los ficheros de otros usuarios se tratan como inexistentes.

        Con un 403 se estaria confirmando que ese identificador esta ocupado.
        """
        stored = await self._files.get_for_owner(file_id, owner_id)
        if stored is None:
            raise FileNotFound(file_id)
        return stored
