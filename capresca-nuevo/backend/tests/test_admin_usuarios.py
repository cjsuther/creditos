"""ABM de usuarios/perfiles y expedientes por oficina."""
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


def test_alta_usuario_y_login(client):
    h = _auth(client)
    r = client.post("/api/admin/usuarios", headers=h, json={
        "username": "jperez", "nombre": "Juan Pérez", "password": "clave123", "perfil": "XCR"})
    assert r.status_code == 201
    # el nuevo usuario puede loguear
    r2 = client.post("/api/auth/login", data={"username": "jperez", "password": "clave123"})
    assert r2.status_code == 200
    # duplicado -> 409
    assert client.post("/api/admin/usuarios", headers=h, json={
        "username": "jperez", "password": "x"}).status_code == 409


def test_cambio_de_clave(client):
    h = _auth(client)
    u = client.post("/api/admin/usuarios", headers=h, json={
        "username": "mgomez", "password": "vieja123", "perfil": "XCJ"}).json()
    client.post(f"/api/admin/usuarios/{u['id']}/clave", headers=h, json={"password": "nueva123"})
    assert client.post("/api/auth/login", data={"username": "mgomez", "password": "nueva123"}).status_code == 200
    assert client.post("/api/auth/login", data={"username": "mgomez", "password": "vieja123"}).status_code == 401


def test_abm_usuario_editar_baja_reactivar(client):
    """ABM completo: editar (nombre+perfil), baja y reactivar."""
    h = _auth(client)
    u = client.post("/api/admin/usuarios", headers=h, json={
        "username": "abmuser", "nombre": "Nombre Viejo", "password": "clave123", "perfil": "XCR"}).json()
    uid = u["id"]
    # editar nombre + perfil
    r = client.put(f"/api/admin/usuarios/{uid}", headers=h, json={"nombre": "Nombre Nuevo", "perfil": "xca"})
    assert r.status_code == 200 and r.json()["nombre"] == "Nombre Nuevo" and r.json()["perfil"] == "XCA"
    # baja → activo False; reactivar → True
    assert client.post(f"/api/admin/usuarios/{uid}/baja", headers=h).json()["activo"] is False
    assert client.post(f"/api/admin/usuarios/{uid}/reactivar", headers=h).json()["activo"] is True


def test_abm_perfiles_crud(client):
    """ABM de perfiles (maeperfil): alta, editar/habilitar, y no se borra si está en uso."""
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "qaperf", "denominacion": "QA Perfil"}).json()
    assert p["codigo"] == "QAPERF" and p["habilitado"] is True
    # duplicado → 409
    assert client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "QAPERF"}).status_code == 409
    # editar denominación + deshabilitar
    e = client.put(f"/api/admin/perfiles-maestro/{p['id']}", headers=h, json={"denominacion": "QA Editado", "habilitado": False})
    assert e.status_code == 200 and e.json()["denominacion"] == "QA Editado" and e.json()["habilitado"] is False
    # asignar el perfil a un usuario → no se puede borrar
    client.post("/api/admin/usuarios", headers=h, json={"username": "conperf", "password": "x1234567", "perfil": "QAPERF"})
    assert client.delete(f"/api/admin/perfiles-maestro/{p['id']}", headers=h).status_code == 409
    # el maestro reporta el uso
    fila = next(x for x in client.get("/api/admin/perfiles-maestro", headers=h).json() if x["codigo"] == "QAPERF")
    assert fila["usuarios"] == 1


def test_perfil_permisos_por_pantalla(client):
    """RBAC: fijar/leer el nivel de acceso de un perfil por pantalla; NINGUNO borra la fila; bulk."""
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "RBAC1", "denominacion": "QA RBAC"}).json()
    pid = p["id"]
    # set CONSULTA en una pantalla
    assert client.put(f"/api/admin/perfiles-maestro/{pid}/permisos", headers=h,
                      json={"ruta": "/creditos/configurar", "nivel": "CONSULTA"}).status_code == 200
    d = client.get(f"/api/admin/perfiles-maestro/{pid}/permisos", headers=h).json()
    assert d["permisos"]["/creditos/configurar"] == "CONSULTA" and "NINGUNO" in d["niveles"]
    # bulk TOTAL en dos pantallas
    client.put(f"/api/admin/perfiles-maestro/{pid}/permisos-bulk", headers=h,
               json={"rutas": ["/creditos/configurar", "/seguridad/usuarios"], "nivel": "TOTAL"})
    d = client.get(f"/api/admin/perfiles-maestro/{pid}/permisos", headers=h).json()
    assert d["permisos"]["/creditos/configurar"] == "TOTAL" and d["permisos"]["/seguridad/usuarios"] == "TOTAL"
    # NINGUNO borra la fila
    client.put(f"/api/admin/perfiles-maestro/{pid}/permisos", headers=h, json={"ruta": "/seguridad/usuarios", "nivel": "NINGUNO"})
    d = client.get(f"/api/admin/perfiles-maestro/{pid}/permisos", headers=h).json()
    assert "/seguridad/usuarios" not in d["permisos"]
    # nivel inválido → 422
    assert client.put(f"/api/admin/perfiles-maestro/{pid}/permisos", headers=h, json={"ruta": "/x", "nivel": "MAGIA"}).status_code == 422


def test_perfil_asignar_usuarios(client):
    """Asignar usuarios a un perfil desde el maestro (les setea el perfil) y listarlos como miembros."""
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "RBAC2", "denominacion": "QA miembros"}).json()
    pid = p["id"]
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "miembro1", "password": "x1234567", "perfil": "XCR"}).json()
    assert client.get(f"/api/admin/perfiles-maestro/{pid}/usuarios", headers=h).json()["usuarios"] == []
    r = client.post(f"/api/admin/perfiles-maestro/{pid}/usuarios", headers=h, json={"usuario_ids": [u["id"]]}).json()
    assert r["asignados"] == 1
    miembros = client.get(f"/api/admin/perfiles-maestro/{pid}/usuarios", headers=h).json()["usuarios"]
    assert [m["username"] for m in miembros] == ["miembro1"]


def test_enforcement_permiso_por_pantalla(client):
    """RBAC efectivo: perfil sin permisos = sin restricciones (legacy); al configurar UNA pantalla el
    perfil pasa a enforcado; el endpoint guardado da 403 sin permiso y 200 con CONSULTA; ADMG siempre."""
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "ENF1", "denominacion": "QA enforce"}).json()
    client.post("/api/admin/usuarios", headers=h, json={"username": "enfuser", "password": "clave12345", "perfil": "ENF1"})
    he = _auth(client, "enfuser", "clave12345")

    # perfil sin filas → sinRestricciones True; la pantalla guardada es accesible
    assert client.get("/api/auth/mis-permisos", headers=he).json()["sinRestricciones"] is True
    assert client.get("/api/contratos/situacion", headers=he).status_code == 200

    # configurar OTRA pantalla → el perfil queda "configurado" (enforcado); situacion pasa a NINGUNO
    client.put(f"/api/admin/perfiles-maestro/{p['id']}/permisos", headers=h,
               json={"ruta": "/creditos/configurar", "nivel": "CONSULTA"})
    assert client.get("/api/auth/mis-permisos", headers=he).json()["sinRestricciones"] is False
    assert client.get("/api/contratos/situacion", headers=he).status_code == 403

    # dar CONSULTA sobre esa pantalla → 200
    client.put(f"/api/admin/perfiles-maestro/{p['id']}/permisos", headers=h,
               json={"ruta": "/creditos/situacion-linea", "nivel": "CONSULTA"})
    assert client.get("/api/contratos/situacion", headers=he).status_code == 200
    # ADMG siempre puede
    assert client.get("/api/contratos/situacion", headers=h).status_code == 200


def test_multi_perfil_union_permisos(client):
    """Multi-rol: un usuario con 2 perfiles ve la UNIÓN de permisos; el endpoint guardado es accesible
    si CUALQUIERA de sus perfiles lo permite."""
    h = _auth(client)
    a = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "MA", "denominacion": "A"}).json()
    b = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "MB", "denominacion": "B"}).json()
    client.put(f"/api/admin/perfiles-maestro/{a['id']}/permisos", headers=h, json={"ruta": "/clientes/maestro", "nivel": "CONSULTA"})
    client.put(f"/api/admin/perfiles-maestro/{b['id']}/permisos", headers=h, json={"ruta": "/creditos/situacion-linea", "nivel": "TOTAL"})
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "multiperfil", "password": "clave123", "perfil": "MA"}).json()
    # asignar ambos perfiles (principal MA + adicional MB)
    r = client.put(f"/api/admin/usuarios/{u['id']}/perfiles", headers=h, json={"principal": "MA", "perfiles": ["MA", "MB"]})
    assert r.status_code == 200 and set(r.json()["perfiles"]) == {"MA", "MB"}
    hu = _auth(client, "multiperfil", "clave123")
    mp = client.get("/api/auth/mis-permisos", headers=hu).json()
    assert mp["sinRestricciones"] is False
    assert mp["permisos"].get("/clientes/maestro") == "CONSULTA"           # de MA
    assert mp["permisos"].get("/creditos/situacion-linea") == "TOTAL"       # de MB
    assert set(mp["perfiles"]) == {"MA", "MB"}
    # el endpoint guardado (situacion) es accesible por el perfil MB
    assert client.get("/api/contratos/situacion", headers=hu).status_code == 200
    # GET perfiles del usuario refleja principal + adicionales
    up = client.get(f"/api/admin/usuarios/{u['id']}/perfiles", headers=h).json()
    assert up["principal"] == "MA" and set(up["perfiles"]) == {"MA", "MB"}


def test_perfiles_y_listado(client):
    h = _auth(client)
    perf = client.get("/api/admin/perfiles", headers=h).json()
    assert any(p["codigo"] == "ADMG" for p in perf)
    us = client.get("/api/admin/usuarios", headers=h).json()
    assert any(u["username"] == "admin" for u in us)


def test_expedientes_por_oficina(client):
    h = _auth(client)
    client.post("/api/despacho/expedientes", headers=h, json={
        "numero": "EXP-2026-777", "caratula": "X", "oficina_inicial": "Mesa de Entradas"})
    r = client.get("/api/despacho/expedientes-por-oficina", headers=h).json()
    assert any(o["oficina"] == "Mesa de Entradas" and o["cantidad"] >= 1 for o in r)
