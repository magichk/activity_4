import os


class Settings:
    """Configuracion leida del fichero de entorno."""

    app_name: str = os.getenv("APP_NAME", "Cloud Activity 4 API")
    app_version: str = os.getenv("APP_VERSION", "0.4.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "postgres://cloud:cloud@db:5432/cloud")
    generate_schemas: bool = os.getenv("GENERATE_SCHEMAS", "true").lower() == "true"

    # Redis: cache de sesiones. El token vive solo aqui, con expiracion nativa, en vez de
    # ocupar una tabla de Postgres que habria que purgar a mano.
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

    # S3 / MinIO: almacenamiento del contenido de los ficheros. Dos endpoints porque el
    # que usa la app para hablar con el bucket (red interna de docker) no es el mismo que
    # el que tiene que ir firmado dentro de una URL prefirmada para que un navegador fuera
    # del docker-compose pueda descargarla.
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
    s3_public_endpoint_url: str = os.getenv("S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", "cloud")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", "cloudcloud")
    s3_bucket: str = os.getenv("S3_BUCKET", "activity-4-files")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    s3_presigned_url_ttl_seconds: int = int(os.getenv("S3_PRESIGNED_URL_TTL_SECONDS", "300"))


settings = Settings()
