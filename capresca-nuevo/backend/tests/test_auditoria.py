"""Auditoría: el login registra evento y la consulta lo devuelve."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def _auth(client):
    r = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_login_registra_auditoria(client):
    h = _auth(client)  # este login ya generó un evento
    eventos = client.get("/api/admin/auditoria?usuario=admin", headers=h).json()["items"]
    assert any(e["proceso"] == "LOGIN" and e["usuario"] == "admin" for e in eventos)


def test_filtro_por_usuario(client):
    h = _auth(client)
    # crear otro usuario y loguear
    client.post("/api/admin/usuarios", headers=h, json={
        "username": "audi", "password": "clave123", "perfil": "XCR"})
    client.post("/api/auth/login", data={"username": "audi", "password": "clave123"})
    eventos = client.get("/api/admin/auditoria?usuario=audi", headers=h).json()["items"]
    assert all("AUDI" in e["usuario"].upper() for e in eventos)
    assert any(e["proceso"] == "LOGIN" for e in eventos)
