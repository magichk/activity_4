from app.config import settings

# Los dos modulos comparten una unica app de Tortoise para que aerich funcione sin parametros.
TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "models": {
            "models": ["app.authentication.models", "app.files.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}
