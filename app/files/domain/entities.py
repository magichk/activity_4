from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    """Metadatos de un fichero, tal y como los guarda Postgres.

    El contenido ya no viaja aqui: vive en S3 y FileService lo consulta aparte a traves de
    FileContentStore. Mezclar los bytes en esta entidad obligaria a cargarlos en memoria
    incluso para operaciones que solo necesitan el nombre, como listar ficheros.
    """

    id: int
    owner_id: int
    name: str
    description: str | None = None
