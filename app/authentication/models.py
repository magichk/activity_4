from tortoise import fields
from tortoise.models import Model


class User(Model):
    """Usuario persistido.

    El identificador externo es el unico que sale de la aplicacion: la clave primaria interna
    no se expone nunca, de modo que se puede cambiar sin afectar a los clientes ni a los ficheros.
    """

    id = fields.IntField(pk=True)
    external_id = fields.IntField(unique=True, index=True)
    email = fields.CharField(max_length=320, unique=True)
    name = fields.CharField(max_length=120, null=True)
    password_hash = fields.CharField(max_length=256)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"


class Session(Model):
    token = fields.CharField(max_length=64, pk=True)
    user = fields.ForeignKeyField("models.User", related_name="sessions", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "sessions"
