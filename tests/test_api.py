"""Pruebas de la API completa contra Postgres, Redis y S3 (MinIO) reales."""

from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.main import app

PASSWORD = "contrasena1"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def pdf_bytes(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def new_email() -> str:
    return f"{uuid4().hex}@example.com"


def register(client: TestClient, email: str):
    return client.post(
        "/authentication/register", json={"email": email, "password": PASSWORD, "name": "Alba"}
    )


def login(client: TestClient, email: str) -> str:
    response = client.post("/authentication/login", json={"email": email, "password": PASSWORD})
    return response.json()["token"]


def new_session(client: TestClient) -> dict[str, str]:
    email = new_email()
    register(client, email)
    return {"Auth": login(client, email)}


def upload(client: TestClient, headers: dict, name: str, pages: int) -> int:
    file_id = client.post("/files", json={"name": name}, headers=headers).json()["id"]
    client.post(
        f"/files/{file_id}",
        files={"upload": (name, pdf_bytes(pages), "application/pdf")},
        headers=headers,
    )
    return file_id


def download(url: str) -> bytes:
    """La URL de descarga es prefirmada y apunta directamente a S3, no a esta API."""
    response = httpx.get(url)
    response.raise_for_status()
    return response.content


def test_el_registro_asigna_identificadores_externos_distintos(client):
    first = register(client, new_email())
    second = register(client, new_email())

    assert first.status_code == 200
    assert first.json()["external_id"] != second.json()["external_id"]


def test_el_registro_repetido_devuelve_409(client):
    email = new_email()
    register(client, email)

    assert register(client, email).status_code == 409


def test_el_login_con_credenciales_incorrectas_devuelve_401(client):
    email = new_email()
    register(client, email)

    response = client.post("/authentication/login", json={"email": email, "password": "equivocada"})
    assert response.status_code == 401


def test_introspect_y_logout(client):
    headers = new_session(client)

    active = client.get("/authentication/introspect", headers=headers)
    assert active.status_code == 200
    assert active.json()["active"] is True

    assert client.post("/authentication/logout", headers=headers).status_code == 200
    assert client.get("/authentication/introspect", headers=headers).status_code == 401


def test_los_endpoints_de_ficheros_exigen_token(client):
    assert client.get("/files").status_code == 422
    assert client.get("/files", headers={"Auth": "inventado"}).status_code == 401


def test_ciclo_completo_de_un_fichero(client):
    headers = new_session(client)

    file_id = client.post(
        "/files", json={"name": "informe.pdf", "description": "notas"}, headers=headers
    ).json()["id"]

    empty = client.get(f"/files/{file_id}", headers=headers).json()
    assert empty["has_content"] is False
    assert empty["download_url"] is None

    response = client.post(
        f"/files/{file_id}",
        files={"upload": ("informe.pdf", pdf_bytes(1), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 200

    filled = client.get(f"/files/{file_id}", headers=headers).json()
    assert filled["has_content"] is True
    assert filled["download_url"] is not None
    assert len(PdfReader(BytesIO(download(filled["download_url"]))).pages) == 1

    assert [f["id"] for f in client.get("/files", headers=headers).json()] == [file_id]
    assert client.delete(f"/files/{file_id}", headers=headers).status_code == 200
    assert client.get(f"/files/{file_id}", headers=headers).status_code == 404


def test_un_usuario_no_ve_los_ficheros_de_otro(client):
    owner = new_session(client)
    intruder = new_session(client)

    file_id = client.post("/files", json={"name": "privado.pdf"}, headers=owner).json()["id"]

    assert client.get("/files", headers=intruder).json() == []
    assert client.get(f"/files/{file_id}", headers=intruder).status_code == 404
    assert client.delete(f"/files/{file_id}", headers=intruder).status_code == 404


def test_merge_suma_las_paginas_de_todos_los_pdfs(client):
    headers = new_session(client)
    ids = [upload(client, headers, f"{pages}.pdf", pages) for pages in (2, 3, 1)]

    merged_id = client.post("/files/merge", json={"file_ids": ids}, headers=headers).json()["id"]

    download_url = client.get(f"/files/{merged_id}", headers=headers).json()["download_url"]
    assert len(PdfReader(BytesIO(download(download_url))).pages) == 6


def test_merge_falla_si_algun_fichero_no_tiene_contenido(client):
    headers = new_session(client)
    first = upload(client, headers, "a.pdf", 1)
    second = client.post("/files", json={"name": "b.pdf"}, headers=headers).json()["id"]

    response = client.post("/files/merge", json={"file_ids": [first, second]}, headers=headers)
    assert response.status_code == 400


def test_merge_no_alcanza_los_ficheros_de_otro_usuario(client):
    owner = new_session(client)
    intruder = new_session(client)
    ajeno = upload(client, owner, "ajeno.pdf", 1)
    propio = upload(client, intruder, "propio.pdf", 1)

    response = client.post("/files/merge", json={"file_ids": [propio, ajeno]}, headers=intruder)
    assert response.status_code == 404
