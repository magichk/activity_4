"""Pruebas del dominio con dobles en memoria, sin base de datos, Redis ni S3 reales."""

import pytest

from app.authentication.domain.security import Pbkdf2PasswordHasher
from app.files.domain.entities import StoredFile
from app.files.domain.errors import FileNotFound, FileWithoutContent, NotEnoughFilesToMerge
from app.files.domain.ports import FileContentStore, FileRepository, PdfMerger, UserResolver
from app.files.domain.services import FileService

# Iteraciones bajas: aqui solo se comprueba el comportamiento, no el coste del hash.
FAST_HASHER = Pbkdf2PasswordHasher(iterations=1_000)


class FakeFileRepository(FileRepository):
    def __init__(self):
        self.rows: dict[int, StoredFile] = {}
        self._next_id = 1

    async def create(self, owner_id: int, name: str, description: str | None) -> int:
        file_id = self._next_id
        self._next_id += 1
        self.rows[file_id] = StoredFile(file_id, owner_id, name, description)
        return file_id

    async def list_for_owner(self, owner_id: int) -> list[StoredFile]:
        return [row for row in self.rows.values() if row.owner_id == owner_id]

    async def get_for_owner(self, file_id: int, owner_id: int) -> StoredFile | None:
        row = self.rows.get(file_id)
        return row if row is not None and row.owner_id == owner_id else None

    async def delete(self, file_id: int) -> bool:
        return self.rows.pop(file_id, None) is not None


class FakeContentStore(FileContentStore):
    """Sustituye a S3: un diccionario en memoria basta para probar el dominio."""

    def __init__(self):
        self.blobs: dict[int, bytes] = {}

    async def put(self, file_id: int, content: bytes) -> None:
        self.blobs[file_id] = content

    async def get(self, file_id: int) -> bytes | None:
        return self.blobs.get(file_id)

    async def exists(self, file_id: int) -> bool:
        return file_id in self.blobs

    async def delete(self, file_id: int) -> None:
        self.blobs.pop(file_id, None)

    async def presigned_download_url(self, file_id: int) -> str | None:
        return f"https://fake-bucket.test/{file_id}" if file_id in self.blobs else None


class FakeMerger(PdfMerger):
    def merge(self, documents: list[bytes]) -> bytes:
        return b"".join(documents)


class FakeUserResolver(UserResolver):
    def __init__(self, external_id: int = 1):
        self.external_id = external_id

    async def external_id_for(self, token: str) -> int:
        return self.external_id


def build_service(
    resolver: FakeUserResolver,
) -> tuple[FileService, FakeFileRepository, FakeContentStore]:
    repository = FakeFileRepository()
    content = FakeContentStore()
    return FileService(repository, content, FakeMerger(), resolver), repository, content


def test_el_hash_no_deja_rastro_de_la_contrasena():
    stored = FAST_HASHER.hash("contrasena1")

    assert "contrasena1" not in stored
    assert FAST_HASHER.verify("contrasena1", stored)
    assert not FAST_HASHER.verify("otra", stored)


def test_dos_hashes_de_la_misma_contrasena_son_distintos():
    assert FAST_HASHER.hash("contrasena1") != FAST_HASHER.hash("contrasena1")


async def test_un_usuario_no_alcanza_los_ficheros_de_otro():
    resolver = FakeUserResolver(external_id=1)
    service, _, _ = build_service(resolver)
    file_id = await service.create("token", "privado.pdf", None)

    resolver.external_id = 2

    assert await service.list_files("token") == []
    with pytest.raises(FileNotFound):
        await service.get("token", file_id)
    with pytest.raises(FileNotFound):
        await service.delete("token", file_id)


async def test_recien_creado_no_tiene_contenido():
    service, _, _ = build_service(FakeUserResolver())
    file_id = await service.create("token", "vacio.pdf", None)

    view = await service.get("token", file_id)

    assert view.has_content is False
    assert await service.download_url("token", file_id) is None


async def test_subir_contenido_habilita_la_url_de_descarga():
    service, _, content = build_service(FakeUserResolver())
    file_id = await service.create("token", "informe.pdf", None)

    await service.set_content("token", file_id, b"contenido")

    view = await service.get("token", file_id)
    assert view.has_content is True
    assert content.blobs[file_id] == b"contenido"
    assert await service.download_url("token", file_id) is not None


async def test_borrar_un_fichero_borra_tambien_su_contenido():
    service, _, content = build_service(FakeUserResolver())
    file_id = await service.create("token", "informe.pdf", None)
    await service.set_content("token", file_id, b"contenido")

    await service.delete("token", file_id)

    assert file_id not in content.blobs


async def test_la_fusion_exige_al_menos_dos_ficheros():
    service, _, _ = build_service(FakeUserResolver())
    file_id = await service.create("token", "solo.pdf", None)

    with pytest.raises(NotEnoughFilesToMerge):
        await service.merge("token", [file_id], None)


async def test_la_fusion_exige_que_todos_tengan_contenido():
    service, _, _ = build_service(FakeUserResolver())
    first = await service.create("token", "a.pdf", None)
    second = await service.create("token", "b.pdf", None)
    await service.set_content("token", first, b"contenido")

    with pytest.raises(FileWithoutContent):
        await service.merge("token", [first, second], None)


async def test_la_fusion_guarda_el_resultado_como_fichero_nuevo():
    service, _, content = build_service(FakeUserResolver())
    ids = []
    for name, data in (("a.pdf", b"aaa"), ("b.pdf", b"bbb")):
        file_id = await service.create("token", name, None)
        await service.set_content("token", file_id, data)
        ids.append(file_id)

    merged_id = await service.merge("token", ids, None)

    assert merged_id not in ids
    assert content.blobs[merged_id] == b"aaabbb"

    merged_view = await service.get("token", merged_id)
    assert merged_view.file.name == "a-b.pdf"
