from app.files.domain.entities import StoredFile
from app.files.domain.ports import FileRepository
from app.files.models import File as FileModel


def to_entity(row: FileModel) -> StoredFile:
    return StoredFile(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
    )


class TortoiseFileRepository(FileRepository):
    """Implementacion del puerto de metadatos de ficheros contra Postgres.

    Solo metadatos: el contenido lo cubre FileContentStore contra S3.
    """

    async def create(self, owner_id: int, name: str, description: str | None) -> int:
        row = await FileModel.create(owner_id=owner_id, name=name, description=description)
        return row.id

    async def list_for_owner(self, owner_id: int) -> list[StoredFile]:
        rows = await FileModel.filter(owner_id=owner_id).order_by("id")
        return [to_entity(row) for row in rows]

    async def get_for_owner(self, file_id: int, owner_id: int) -> StoredFile | None:
        row = await FileModel.get_or_none(id=file_id, owner_id=owner_id)
        return None if row is None else to_entity(row)

    async def delete(self, file_id: int) -> bool:
        return await FileModel.filter(id=file_id).delete() > 0
