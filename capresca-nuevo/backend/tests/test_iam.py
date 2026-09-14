"""IAM: Usuario → Grupo → Rol → Permiso, con grants directos y vigencia temporal."""
import datetime
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


def test_iam_cadena_grupo_rol_permiso(client):
    """El usuario hereda los permisos de los roles de sus grupos (usuario→grupo→rol→permiso)."""
    h = _auth(client)
    rol = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IAMR", "denominacion": "rol"}).json()
    client.put(f"/api/admin/perfiles-maestro/{rol['id']}/permisos", headers=h, json={"ruta": "/clientes/maestro", "nivel": "CONSULTA"})
    g = client.post("/api/admin/grupos", headers=h, json={"codigo": "IAMG", "nombre": "grupo"}).json()
    assert client.put(f"/api/admin/grupos/{g['id']}/roles", headers=h, json={"roles": ["IAMR"]}).status_code == 200
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "iamuser", "password": "clave123", "perfil": "XCR"}).json()
    assert client.post(f"/api/admin/usuarios/{u['id']}/grupos", headers=h, json={"grupo": "IAMG"}).status_code == 200
    mp = client.get("/api/auth/mis-permisos", headers=_auth(client, "iamuser", "clave123")).json()
    assert mp["permisos"].get("/clientes/maestro") == "CONSULTA"     # heredado del grupo → rol
    assert "IAMR" in mp["roles"]


def test_iam_mutaciones_dejan_auditoria(client):
    """H-155: las mutaciones de Seguridad (usuarios/roles/grupos) dejan rastro en auditoría con quién,
    qué operación y la IP. Antes sólo se auditaba el LOGIN."""
    h = _auth(client)
    # alta de usuario (con IP de origen) + alta de grupo
    u = client.post("/api/admin/usuarios", headers={**h, "X-Forwarded-For": "203.0.113.9"},
                    json={"username": "audituser", "password": "clave123", "perfil": "XCR"}).json()
    client.post("/api/admin/grupos", headers=h, json={"codigo": "AUDG", "nombre": "g audit"})
    # el alta de usuario quedó auditada con IP y actor
    d = client.get("/api/admin/auditoria-cambios", headers=h, params={"entidad": "Usuario", "operacion": "CREAR"}).json()
    ev = next(e for e in d["items"] if str(e["entidad_id"]) == str(u["id"]))
    assert ev["usuario"] == "admin" and ev["ip"] == "203.0.113.9" and ev["resultado"] == "OK"
    # el alta de grupo también
    g = client.get("/api/admin/auditoria-cambios", headers=h, params={"entidad": "Grupo", "operacion": "CREAR"}).json()
    assert any(str(e["entidad_id"]) == "AUDG" for e in g["items"])


def test_grupo_inactivo_no_otorga_acceso(client):
    """H-153: DESACTIVAR un grupo (activo=False) corta el acceso heredado de todos sus miembros de una,
    sin tener que quitar la membresía. Antes `roles_de` ignoraba `Grupo.activo` y seguía otorgando el rol."""
    h = _auth(client)
    rol = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "GIAR", "denominacion": "rol"}).json()
    client.put(f"/api/admin/perfiles-maestro/{rol['id']}/permisos", headers=h, json={"ruta": "/clientes/maestro", "nivel": "CONSULTA"})
    g = client.post("/api/admin/grupos", headers=h, json={"codigo": "GIAG", "nombre": "grupo"}).json()
    client.put(f"/api/admin/grupos/{g['id']}/roles", headers=h, json={"roles": ["GIAR"]})
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "giauser", "password": "clave123", "perfil": "XCR"}).json()
    client.post(f"/api/admin/usuarios/{u['id']}/grupos", headers=h, json={"grupo": "GIAG"})
    # con el grupo activo, hereda el rol y el permiso
    mp = client.get("/api/auth/mis-permisos", headers=_auth(client, "giauser", "clave123")).json()
    assert mp["permisos"].get("/clientes/maestro") == "CONSULTA" and "GIAR" in mp["roles"]
    # desactivar el grupo → deja de otorgar rol y permiso (misma membresía)
    assert client.put(f"/api/admin/grupos/{g['id']}", headers=h, json={"codigo": "GIAG", "nombre": "grupo", "activo": False}).status_code == 200
    mp2 = client.get("/api/auth/mis-permisos", headers=_auth(client, "giauser", "clave123")).json()
    assert "GIAR" not in mp2["roles"]
    assert mp2["permisos"].get("/clientes/maestro") is None


def test_iam_vigencia_vence_el_acceso(client):
    """Un grupo con vigencia vencida deja de otorgar acceso (cobertura de licencia que se apaga sola)."""
    h = _auth(client)
    rol = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IAV", "denominacion": "rol"}).json()
    client.put(f"/api/admin/perfiles-maestro/{rol['id']}/permisos", headers=h, json={"ruta": "/seguros/polizas", "nivel": "TOTAL"})
    g = client.post("/api/admin/grupos", headers=h, json={"codigo": "IAVG", "nombre": "grupo"}).json()
    client.put(f"/api/admin/grupos/{g['id']}/roles", headers=h, json={"roles": ["IAV"]})
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "iavuser", "password": "clave123", "perfil": "XCR"}).json()
    hu = _auth(client, "iavuser", "clave123")
    hoy = datetime.date.today()
    # vigente (hasta mañana) → tiene acceso
    client.post(f"/api/admin/usuarios/{u['id']}/grupos", headers=h,
                json={"grupo": "IAVG", "hasta": str(hoy + datetime.timedelta(days=1))})
    assert client.get("/api/auth/mis-permisos", headers=hu).json()["permisos"].get("/seguros/polizas") == "TOTAL"
    # vencido (hasta ayer) → sin acceso, y como no le queda ningún rol configurado, vuelve a sin restricciones
    ayer = str(hoy - datetime.timedelta(days=1))
    client.post(f"/api/admin/usuarios/{u['id']}/grupos", headers=h, json={"grupo": "IAVG", "desde": "2020-01-01", "hasta": ayer})
    mp = client.get("/api/auth/mis-permisos", headers=hu).json()
    assert "/seguros/polizas" not in mp["permisos"]
    # accesos: refleja el grupo con su vencimiento
    acc = client.get(f"/api/admin/usuarios/{u['id']}/accesos", headers=h).json()
    assert any(x["codigo"] == "IAVG" and x["hasta"] == ayer for x in acc["grupos"])


def test_iam_permiso_directo_vigencia(client):
    """Un permiso directo sobre una pantalla se otorga con vigencia y se corta al vencer o al quitarlo."""
    h = _auth(client)
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "ipduser", "password": "clave123", "perfil": "XCR"}).json()
    # además le damos un rol configurado para que NO caiga en "sin restricciones" y el permiso directo sea el que aporta la pantalla
    rol = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IPDR", "denominacion": "rol"}).json()
    client.put(f"/api/admin/perfiles-maestro/{rol['id']}/permisos", headers=h, json={"ruta": "/caja/cobranza", "nivel": "CONSULTA"})
    client.put(f"/api/admin/usuarios/{u['id']}/perfiles", headers=h, json={"principal": "IPDR", "perfiles": ["IPDR"]})
    hu = _auth(client, "ipduser", "clave123")
    # permiso directo vigente sobre otra pantalla
    hoy = datetime.date.today()
    r = client.post(f"/api/admin/usuarios/{u['id']}/permisos-directos", headers=h,
                    json={"ruta": "/seguros/polizas", "nivel": "TOTAL", "hasta": str(hoy + datetime.timedelta(days=1))})
    assert r.status_code == 200
    assert client.get("/api/auth/mis-permisos", headers=hu).json()["permisos"].get("/seguros/polizas") == "TOTAL"
    # figura en accesos
    acc = client.get(f"/api/admin/usuarios/{u['id']}/accesos", headers=h).json()
    assert any(p["ruta"] == "/seguros/polizas" and p["nivel"] == "TOTAL" for p in acc["permisosDirectos"])
    # vencido → deja de aplicar
    client.post(f"/api/admin/usuarios/{u['id']}/permisos-directos", headers=h,
                json={"ruta": "/seguros/polizas", "nivel": "TOTAL", "desde": "2020-01-01", "hasta": str(hoy - datetime.timedelta(days=1))})
    assert "/seguros/polizas" not in client.get("/api/auth/mis-permisos", headers=hu).json()["permisos"]
    # nivel NINGUNO borra la fila
    client.post(f"/api/admin/usuarios/{u['id']}/permisos-directos", headers=h, json={"ruta": "/seguros/polizas", "nivel": "NINGUNO"})
    acc = client.get(f"/api/admin/usuarios/{u['id']}/accesos", headers=h).json()
    assert not any(p["ruta"] == "/seguros/polizas" for p in acc["permisosDirectos"])
    # ruta inválida → 422
    assert client.post(f"/api/admin/usuarios/{u['id']}/permisos-directos", headers=h,
                       json={"ruta": "sin-barra", "nivel": "TOTAL"}).status_code == 422


def test_iam_grupo_borrar_en_uso_409(client):
    h = _auth(client)
    g = client.post("/api/admin/grupos", headers=h, json={"codigo": "IAUSO", "nombre": "g"}).json()
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "iusog", "password": "clave123", "perfil": "XCR"}).json()
    client.post(f"/api/admin/usuarios/{u['id']}/grupos", headers=h, json={"grupo": "IAUSO"})
    assert client.delete(f"/api/admin/grupos/{g['id']}", headers=h).status_code == 409
    client.delete(f"/api/admin/usuarios/{u['id']}/grupos/IAUSO", headers=h)
    assert client.delete(f"/api/admin/grupos/{g['id']}", headers=h).status_code == 200


def test_iam_asignar_rol_es_aditivo(client):
    """Sumar un rol a un usuario desde la pantalla de Roles NO pisa su rol principal:
    lo agrega como rol adicional (multi-rol), aparece como miembro no-principal y suma al conteo."""
    h = _auth(client)
    rol = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IADI", "denominacion": "adic"}).json()
    u = client.post("/api/admin/usuarios", headers=h, json={"username": "iadiuser", "password": "clave123", "perfil": "XCR"}).json()
    r = client.post(f"/api/admin/perfiles-maestro/{rol['id']}/usuarios", headers=h, json={"usuario_ids": [u["id"]]})
    assert r.status_code == 200 and r.json()["asignados"] == 1
    # el principal sigue siendo XCR y ahora tiene IADI como adicional
    per = client.get(f"/api/admin/usuarios/{u['id']}/perfiles", headers=h).json()
    assert per["principal"] == "XCR" and set(per["perfiles"]) == {"XCR", "IADI"}
    # figura como miembro del rol con principal=False
    miembros = client.get(f"/api/admin/perfiles-maestro/{rol['id']}/usuarios", headers=h).json()["usuarios"]
    assert any(m["username"] == "iadiuser" and m["principal"] is False for m in miembros)
    # el conteo del rol en la grilla incluye al miembro adicional
    grilla = client.get("/api/admin/perfiles-maestro", headers=h).json()
    assert [p for p in grilla if p["codigo"] == "IADI"][0]["usuarios"] == 1
    # reasignar es idempotente
    assert client.post(f"/api/admin/perfiles-maestro/{rol['id']}/usuarios", headers=h, json={"usuario_ids": [u["id"]]}).json()["asignados"] == 0
    # no se puede borrar el rol mientras sea rol adicional de alguien
    assert client.delete(f"/api/admin/perfiles-maestro/{rol['id']}", headers=h).status_code == 409


def test_iam_borrar_rol_bloqueado_por_grupo(client):
    """Un rol incluido en un grupo no se puede borrar (integridad de la cadena grupo→rol)."""
    h = _auth(client)
    rol = client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IGRR", "denominacion": "x"}).json()
    g = client.post("/api/admin/grupos", headers=h, json={"codigo": "IGRRG", "nombre": "g"}).json()
    client.put(f"/api/admin/grupos/{g['id']}/roles", headers=h, json={"roles": ["IGRR"]})
    assert client.delete(f"/api/admin/perfiles-maestro/{rol['id']}", headers=h).status_code == 409
    client.put(f"/api/admin/grupos/{g['id']}/roles", headers=h, json={"roles": []})
    assert client.delete(f"/api/admin/perfiles-maestro/{rol['id']}", headers=h).status_code == 200


def test_iam_rol_codigo_unico(client):
    """El código de rol es único (chequeo app + constraint DB como árbitro)."""
    h = _auth(client)
    assert client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IUNQ", "denominacion": "a"}).status_code == 201
    assert client.post("/api/admin/perfiles-maestro", headers=h, json={"codigo": "IUNQ", "denominacion": "b"}).status_code == 409
