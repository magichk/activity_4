from tortoise import fields
from tortoise.models import Model


class File(Model):
    """Metadatos del fichero persistidos en Postgres.

    El propietario se guarda por su identificador externo, que es el que viaja por la API.
    Desde la actividad 4 el contenido ya no vive aqui: esta tabla solo describe el fichero,
    los bytes estan en S3 y los gestiona FileContentStore.
    """

    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField(
        "models.User",
        related_name="files",
        to_field="external_id",
        source_field="owner_external_id",
        on_delete=fields.CASCADE,
    )
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "files"
