"""QA intenso de Usuarios y Perfiles: validaciones, edge cases y candados de seguridad.
Las aserciones expresan la conducta CORRECTA esperada; las que fallen son bugs a corregir.
"""
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


# ───────────── Usuarios ─────────────
def test_qa_alta_usuario_password_vacio_rechazado(client):
    """No se debe poder crear un usuario con contraseña vacía (login con clave vacía sería un agujero)."""
    h = _auth(client)
    r = client.post("/api/admin/usuarios", headers=h, json={"username": "vacio1", "password": "", "perfil": "XCR"})
    assert r.status_code == 422, f"alta con password vacío devolvió {r.status_code}"


def test_qa_alta_usuario_password_corto_rechazado(client):
    """Política mínima de clave (>= 6)."""
    h = _auth(client)
    r = client.post("/api/admin/usuarios", headers=h, json={"username": "corto1", "password": "123", "perfil": "XCR"})
    assert r.status_code == 422, f"alta con password corto devolvió {r.status_code}"


def test_qa_alta_usuario_username_vacio_rechazado(client):
    h = _auth(client)
    r = client.post("/api/admin/usuarios", headers=h, json={"username": "  ", "password": "clave123", "perfil": "XCR"})
    assert r.status_code == 422, f"alta con username vacío devolvió {r.status_code}"


def test_qa_reset_clave_vacia_rechazada(client):
    h = _auth(client)
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "resetvacio", "password": "clave123", "perfil": "XCR"}).json()
    r = client.post(f"/api/admin/usuarios/{u['id']}/clave", headers=h, json={"password": ""})
    assert r.status_code == 422, f"reset con clave vacía devolvió {r.status_code}"


def test_qa_no_autobaja_del_propio_usuario(client):
    """Un usuario no debería poder darse de baja a sí mismo (lockout)."""
    h = _auth(client)
    admin = next(u for u in client.get("/api/admin/usuarios", headers=h).json() if u["username"] == "admin")
    r = client.post(f"/api/admin/usuarios/{admin['id']}/baja", headers=h)
    assert r.status_code == 409, f"autobaja devolvió {r.status_code} (riesgo de lockout)"


def test_qa_no_baja_ultimo_admin(client):
    """No dejar el sistema sin ningún administrador activo."""
    h = _auth(client)
    admins = [u for u in client.get("/api/admin/usuarios", headers=h).json() if u["perfil"] == "ADMG" and u["activo"]]
    if len(admins) != 1:
        pytest.skip("el test aplica cuando hay un único admin")
    r = client.post(f"/api/admin/usuarios/{admins[0]['id']}/baja", headers=h)
    assert r.status_code == 409, "se pudo dar de baja al último admin"


def test_qa_no_degradar_ultimo_admin(client):
    """H-154: no dejar el sistema sin admin por otras vías que la baja — cambiar el perfil principal del
    último ADMG (editar_usuario / set-perfiles) o deshabilitar el rol ADMG debe dar 409."""
    h = _auth(client)
    admins = [u for u in client.get("/api/admin/usuarios", headers=h).json() if u["perfil"] == "ADMG" and u["activo"]]
    if len(admins) != 1:
        pytest.skip("el test aplica cuando hay un único admin")
    aid = admins[0]["id"]
    # 1) editar_usuario: degradar a XCR → 409
    assert client.put(f"/api/admin/usuarios/{aid}", headers=h, json={"perfil": "XCR"}).status_code == 409
    # 2) set-perfiles: principal no-ADMG → 409
    assert client.put(f"/api/admin/usuarios/{aid}/perfiles", headers=h,
                      json={"principal": "XCR", "perfiles": ["XCR"]}).status_code == 409
    # 3) deshabilitar el rol ADMG → 409
    admg = next(p for p in client.get("/api/admin/perfiles-maestro", headers=h).json() if p["codigo"] == "ADMG")
    assert client.put(f"/api/admin/perfiles-maestro/{admg['id']}", headers=h,
                      json={"denominacion": admg["denominacion"], "habilitado": False}).status_code == 409
    # el admin sigue pudiendo entrar
    assert client.post("/api/auth/login", data={"username": "admin", "password": "admin123"}).status_code == 200


def test_qa_usuario_baja_no_puede_loguear(client):
    """Persistencia real: un usuario dado de baja no puede iniciar sesión; reactivado sí."""
    h = _auth(client)
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "bajalogin", "password": "clave123", "perfil": "XCR"}).json()
    assert client.post("/api/auth/login", data={"username": "bajalogin", "password": "clave123"}).status_code == 200
    client.post(f"/api/admin/usuarios/{u['id']}/baja", headers=h)
    assert client.post("/api/auth/login", data={"username": "bajalogin", "password": "clave123"}).status_code == 401
    client.post(f"/api/admin/usuarios/{u['id']}/reactivar", headers=h)
    assert client.post("/api/auth/login", data={"username": "bajalogin", "password": "clave123"}).status_code == 200


# ───────────── Perfiles ─────────────
def test_qa_perfil_codigo_largo_rechazado(client):
    """El código de perfil no puede exceder 6 chars (columna varchar(6))."""
    h = _auth(client)
    r = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "DEMASIADOLARGO", "denominacion": "x"})
    assert r.status_code == 422, f"código largo devolvió {r.status_code}"


def test_qa_perfil_borrar_cascada_permisos(client):
    """Borrar un perfil (sin usuarios) borra también sus permisos por pantalla (sin FK colgada)."""
    from app import models
    from app.core.database import SessionLocal
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "CASC1", "denominacion": "cascada"}).json()
    client.put(f"/api/admin/perfiles-maestro/{p['id']}/permisos", headers=h, json={"ruta": "/creditos/configurar", "nivel": "TOTAL"})
    assert client.delete(f"/api/admin/perfiles-maestro/{p['id']}", headers=h).status_code == 200
    with SessionLocal() as db:
        assert db.query(models.PerfilPermiso).filter_by(perfil_codigo="CASC1").count() == 0


def test_qa_perfil_deshabilitado_bloquea_a_sus_usuarios(client):
    """Un perfil deshabilitado debería negar el acceso a sus usuarios (login o RBAC)."""
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "DESH1", "denominacion": "deshab"}).json()
    client.post("/api/admin/usuarios", headers=h, json={"username": "deshuser", "password": "clave123", "perfil": "DESH1"})
    # deshabilitar el perfil
    client.put(f"/api/admin/perfiles-maestro/{p['id']}", headers=h, json={"denominacion": "deshab", "habilitado": False})
    # el usuario no debería poder loguear (o quedar sin acceso)
    r = client.post("/api/auth/login", data={"username": "deshuser", "password": "clave123"})
    assert r.status_code in (401, 403), f"usuario de perfil deshabilitado pudo loguear ({r.status_code})"


def test_qa_permiso_ruta_malformada_rechazada(client):
    """No aceptar rutas de pantalla malformadas (vacías o sin '/') como permiso."""
    h = _auth(client)
    p = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "RUTA1", "denominacion": "ruta"}).json()
    assert client.put(f"/api/admin/perfiles-maestro/{p['id']}/permisos", headers=h, json={"ruta": "", "nivel": "TOTAL"}).status_code == 422
    assert client.put(f"/api/admin/perfiles-maestro/{p['id']}/permisos", headers=h, json={"ruta": "sin-barra", "nivel": "TOTAL"}).status_code == 422
