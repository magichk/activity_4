from pydantic import BaseModel, Field


class FileMetadataRequest(BaseModel):
    name: str = Field(description="Nombre del fichero")
    description: str | None = Field(default=None, description="Descripcion libre")


class FileSummary(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None = None
    has_content: bool = Field(description="Si tiene contenido subido a S3")


class FileDetail(FileSummary):
    download_url: str | None = Field(
        default=None,
        description="URL firmada y temporal para descargar el contenido directamente de S3",
    )


class FileCreatedResponse(BaseModel):
    id: int


class MergeRequest(BaseModel):
    file_ids: list[int] = Field(min_length=2, description="Identificadores de los PDFs a fusionar")
    name: str | None = Field(default=None, description="Nombre del PDF resultante")


class MessageResponse(BaseModel):
    detail: str
