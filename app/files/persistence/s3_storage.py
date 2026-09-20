import asyncio

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.files.domain.ports import FileContentStore

NOT_FOUND_CODES = {"404", "NoSuchKey"}


def _object_key(file_id: int) -> str:
    return f"files/{file_id}"


class S3FileContentStore(FileContentStore):
    """Implementacion del puerto de contenido contra S3 (aqui, MinIO).

    boto3 es sincrono, asi que cada llamada de red va envuelta en asyncio.to_thread para no
    bloquear el event loop de FastAPI mientras responde.

    Usa dos clientes a proposito: uno con el endpoint interno de docker-compose (con el que
    la app sube, baja y borra objetos) y otro con el endpoint publico, solo para firmar URLs
    de descarga. SigV4 firma la cabecera Host, asi que una URL firmada contra "minio:9000" no
    la puede abrir un navegador fuera de la red de docker; hay que firmarla ya con el host
    que el cliente va a usar de verdad.
    """

    def __init__(self):
        client_kwargs = {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
            "config": Config(signature_version="s3v4"),
        }
        self._client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url, **client_kwargs)
        self._public_client = boto3.client(
            "s3", endpoint_url=settings.s3_public_endpoint_url, **client_kwargs
        )
        self._bucket = settings.s3_bucket

    async def ensure_bucket(self) -> None:
        """Crea el bucket si todavia no existe. MinIO arranca vacio, a diferencia de un
        bucket de S3 real que ya se habria creado a mano una vez."""
        await asyncio.to_thread(self._ensure_bucket_sync)

    def _ensure_bucket_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    async def put(self, file_id: int, content: bytes) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=_object_key(file_id),
            Body=content,
        )

    async def get(self, file_id: int) -> bytes | None:
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=_object_key(file_id)
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in NOT_FOUND_CODES:
                return None
            raise
        return await asyncio.to_thread(response["Body"].read)

    async def exists(self, file_id: int) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object, Bucket=self._bucket, Key=_object_key(file_id)
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in NOT_FOUND_CODES:
                return False
            raise
        return True

    async def delete(self, file_id: int) -> None:
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self._bucket, Key=_object_key(file_id)
        )

    async def presigned_download_url(self, file_id: int) -> str | None:
        if not await self.exists(file_id):
            return None
        return await asyncio.to_thread(
            self._public_client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": _object_key(file_id)},
            ExpiresIn=settings.s3_presigned_url_ttl_seconds,
        )
