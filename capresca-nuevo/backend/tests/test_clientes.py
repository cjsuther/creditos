"""Maestro de clientes: alta con CUIL único (la DB es árbitro) + idempotencia (H-154)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def _auth(client, user="admin", pw="admin123"):
    r = client.post("/api/auth/login", data={"username": user, "password": pw})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_alta_cliente_cuil_unico_y_dv(client):
    """CUIL único (constraint = árbitro): dos altas con el mismo CUIL y distinto código → 409, no
    duplicado. CUIL con dígito verificador inválido → 422."""
    h = _auth(client)
    base = {"id_cliente": "T001", "cuil": "20111111112", "apellido_nombre": "TEST UNO"}
    assert client.post("/api/clientes", headers=h, json=base).status_code == 201
    # mismo CUIL, distinto código → 409 (no crea duplicado)
    assert client.post("/api/clientes", headers=h, json={**base, "id_cliente": "T002"}).status_code == 409
    # CUIL con DV inválido → 422
    assert client.post("/api/clientes", headers=h,
                       json={**base, "id_cliente": "T003", "cuil": "27234567818"}).status_code == 422
    # sólo quedó 1 con ese CUIL
    items = client.get("/api/clientes?q=20111111112", headers=h).json()["items"]
    assert len([c for c in items if c["cuil"] == "20111111112"]) == 1


def test_escritura_cliente_exige_permiso_backend(client):
    """H-156: el RBAC fino se enforca en el BACKEND, no sólo en el front. Un rol con CONSULTA sobre
    /clientes/maestro NO puede crear/editar/dar de baja (403); ADMG (sin_restricciones) sí."""
    h = _auth(client)
    rol = client.post("/api/admin/perfiles-maestro", headers=h,
                      json={"codigo": "RCLI", "denominacion": "solo lectura clientes"}).json()
    client.put(f"/api/admin/perfiles-maestro/{rol['id']}/permisos", headers=h,
               json={"ruta": "/clientes/maestro", "nivel": "CONSULTA"})
    client.post("/api/admin/usuarios", headers=h, json={"username": "lector", "password": "clave123", "perfil": "RCLI"})
    hl = _auth(client, "lector", "clave123")
    body = {"id_cliente": "RB1", "cuil": "20111111112", "apellido_nombre": "RBAC"}
    # CONSULTA no alcanza para crear → 403
    assert client.post("/api/clientes", headers=hl, json=body).status_code == 403
    # admin (sin_restricciones) sí crea
    assert client.post("/api/clientes", headers=h, json=body).status_code == 201


def test_alta_cliente_idempotente(client):
    """Idempotency-Key: reintento con la misma clave no crea dos clientes (devuelve el mismo)."""
    h = {**_auth(client), "Idempotency-Key": "cliente-k1"}
    body = {"id_cliente": "IDEM1", "cuil": "20111111112", "apellido_nombre": "IDEM"}
    r1 = client.post("/api/clientes", headers=h, json=body)
    r2 = client.post("/api/clientes", headers=h, json=body)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]        # mismo cliente, no duplicado
