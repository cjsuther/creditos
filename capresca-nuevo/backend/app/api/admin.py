"""Módulo Utilidades / Tablas: ABMs de tablas maestras y configuración.

Reemplaza pantallas VFP como Administración de Líneas de Créditos
(frm305050000lineas), Consulta/ABM de Organismos, parámetros generales, etc.
Restringido a perfil Administrador (ADMG) o Utilidades.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, PERFILES
from app.deps import requiere_perfil, get_current_user
from app.services import auditoria as audit
from app import models, schemas


# ── Auditoría de IAM (H-155): quién hizo qué en Seguridad, con antes/después + IP ──
# `_actor` inyecta (usuario, perfil, ip) del que ejecuta; `_audit` deja el rastro. Antes las mutaciones de
# usuarios/roles/grupos/permisos no dejaban traza (sólo se auditaba el LOGIN), grave para un módulo de seguridad.
def _actor(request: Request, actual: models.Usuario = Depends(get_current_user)) -> tuple[str, str, str]:
    return (actual.username, (actual.perfil or ""), audit.ip_de(request))


def _audit(db: Session, actor: tuple[str, str, str], entidad: str, entidad_id, operacion: str,
           *, resultado: str = "OK", antes: dict | None = None, despues: dict | None = None, detalle: str = ""):
    u, p, ip = actor
    audit.registrar_cambio(db, usuario=u, perfil=p, ip=ip, entidad=entidad,
                           entidad_id=(str(entidad_id) if entidad_id is not None else None),
                           operacion=operacion, resultado=resultado, antes=antes, despues=despues, detalle=detalle)


def _commit_unico(db: Session, mensaje: str):
    """Commit que traduce la violación de unicidad de la DB (carrera concurrente) a 409.
    La DB es el árbitro de la unicidad; el chequeo previo sólo mejora el mensaje feliz."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, mensaje)

router = APIRouter(prefix="/api/admin", tags=["admin"],
                   dependencies=[Depends(requiere_perfil("AD"))])  # ADMG siempre pasa


# ---------------- Líneas de crédito ----------------
@router.get("/lineas", response_model=list[schemas.LineaAdminOut])
def lineas(db: Session = Depends(get_db)):
    return db.scalars(select(models.LineaCredito).order_by(models.LineaCredito.nombre)).all()


@router.post("/lineas", response_model=schemas.LineaAdminOut, status_code=201)
def crear_linea(data: schemas.LineaCreate, db: Session = Depends(get_db)):
    linea = models.LineaCredito(**data.model_dump())
    db.add(linea)
    db.commit()
    db.refresh(linea)
    return linea


@router.put("/lineas/{linea_id}", response_model=schemas.LineaAdminOut)
def editar_linea(linea_id: int, data: schemas.LineaCreate, db: Session = Depends(get_db)):
    linea = db.get(models.LineaCredito, linea_id)
    if not linea:
        raise HTTPException(404, "Línea no encontrada")
    for k, v in data.model_dump().items():
        setattr(linea, k, v)
    db.commit()
    db.refresh(linea)
    return linea


# ---------------- Organismos ----------------
@router.get("/organismos", response_model=list[schemas.OrganismoAdminOut])
def organismos(db: Session = Depends(get_db)):
    return db.scalars(select(models.Organismo).order_by(models.Organismo.nombre)).all()


@router.get("/proveedores", response_model=list[schemas.ProveedorOut])
def proveedores(q: str | None = None, db: Session = Depends(get_db)):
    """Maestro de proveedores (VFP: proveedores)."""
    qy = select(models.Proveedor)
    if q:
        like = f"%{q.upper()}%"
        qy = qy.where(models.Proveedor.razon_social.like(like) | models.Proveedor.cuit.like(like))
    return db.scalars(qy.order_by(models.Proveedor.razon_social)).all()


@router.post("/proveedores", response_model=schemas.ProveedorOut, status_code=201)
def crear_proveedor(data: schemas.ProveedorUpsert, db: Session = Depends(get_db)):
    p = models.Proveedor(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.post("/organismos", response_model=schemas.OrganismoAdminOut, status_code=201)
def crear_organismo(data: schemas.OrganismoUpsert, db: Session = Depends(get_db)):
    o = models.Organismo(**data.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/organismos/{org_id}", response_model=schemas.OrganismoAdminOut)
def editar_organismo(org_id: int, data: schemas.OrganismoUpsert, db: Session = Depends(get_db)):
    o = db.get(models.Organismo, org_id)
    if not o:
        raise HTTPException(404, "Organismo no encontrado")
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


# ---------------- Compañías de seguros ----------------
@router.get("/companias", response_model=list[schemas.CompaniaOut])
def companias(db: Session = Depends(get_db)):
    return db.scalars(select(models.CompaniaSeguros).order_by(models.CompaniaSeguros.nombre)).all()


@router.post("/companias", response_model=schemas.CompaniaOut, status_code=201)
def crear_compania(data: schemas.CompaniaUpsert, db: Session = Depends(get_db)):
    c = models.CompaniaSeguros(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------------- Parámetros generales ----------------
@router.get("/parametros", response_model=list[schemas.ParametroOut])
def parametros(ambito: str | None = None, db: Session = Depends(get_db)):
    """Parámetros. Filtrables por ámbito (general|creditos|contabilidad) — H-197."""
    qy = select(models.Parametro)
    if ambito:
        qy = qy.where(models.Parametro.ambito == ambito)
    return db.scalars(qy.order_by(models.Parametro.clave)).all()


@router.post("/parametros", response_model=schemas.ParametroOut, status_code=201)
def upsert_parametro(data: schemas.ParametroUpsert, db: Session = Depends(get_db)):
    p = db.scalar(select(models.Parametro).where(models.Parametro.clave == data.clave))
    if p:
        p.valor = data.valor
        p.descripcion = data.descripcion
        if data.ambito:
            p.ambito = data.ambito
    else:
        p = models.Parametro(**data.model_dump())
        db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------- Usuarios y perfiles ----------------
@router.get("/usuarios")
def usuarios(db: Session = Depends(get_db)):
    extras = dict(db.execute(select(models.UsuarioPerfil.usuario_id, func.count())
                             .group_by(models.UsuarioPerfil.usuario_id)).all())
    return [{"id": u.id, "username": u.username, "nombre": u.nombre, "perfil": u.perfil,
             "activo": u.activo, "perfilesExtra": extras.get(u.id, 0)}
            for u in db.scalars(select(models.Usuario).order_by(models.Usuario.username)).all()]


MIN_CLAVE = 6


def _validar_clave(pw: str) -> None:
    if not pw or len(pw) < MIN_CLAVE:
        raise HTTPException(422, f"La contraseña debe tener al menos {MIN_CLAVE} caracteres.")


@router.post("/usuarios", response_model=schemas.UsuarioOut, status_code=201)
def crear_usuario(data: schemas.UsuarioCreate, db: Session = Depends(get_db),
                  actor: tuple = Depends(_actor)):
    username = (data.username or "").strip()
    if not username:
        raise HTTPException(422, "El nombre de usuario es obligatorio.")
    if db.scalar(select(models.Usuario).where(models.Usuario.username == username)):
        raise HTTPException(409, "Ya existe un usuario con ese nombre")
    _validar_clave(data.password)
    u = models.Usuario(username=username, nombre=data.nombre,
                       password_hash=hash_password(data.password),
                       perfil=(data.perfil or "XCR").upper(), activo=True)
    db.add(u); _commit_unico(db, "Ya existe un usuario con ese nombre"); db.refresh(u)
    _audit(db, actor, "Usuario", u.id, "CREAR",
           despues={"username": u.username, "perfil": u.perfil}, detalle=f"Alta de usuario {u.username}")
    return u


@router.post("/usuarios/{usuario_id}/clave", response_model=schemas.UsuarioOut)
def cambiar_clave(usuario_id: int, data: schemas.CambioClave, db: Session = Depends(get_db),
                  actor: tuple = Depends(_actor)):
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    _validar_clave(data.password)
    u.password_hash = hash_password(data.password)
    db.commit(); db.refresh(u)
    _audit(db, actor, "Usuario", u.id, "CLAVE", detalle=f"Reset de contraseña de {u.username}")
    return u


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    perfil: str | None = None


def _es_ultimo_admg(db: Session, excluir_id: int) -> bool:
    """¿`excluir_id` es el ÚNICO ADMG (perfil principal) activo? (H-154) — para no dejar el sistema sin
    administrador al degradar su perfil."""
    otros = db.scalar(select(func.count()).select_from(models.Usuario).where(
        models.Usuario.perfil == "ADMG", models.Usuario.activo.is_(True), models.Usuario.id != excluir_id))
    return not otros


@router.put("/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
def editar_usuario(usuario_id: int, data: UsuarioUpdate, db: Session = Depends(get_db),
                   actor: tuple = Depends(_actor)):
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    antes = {"nombre": u.nombre, "perfil": u.perfil}
    if data.nombre is not None:
        u.nombre = data.nombre
    if data.perfil is not None:
        cod = data.perfil.strip().upper()
        if not cod:
            raise HTTPException(422, "El perfil no puede quedar vacío.")
        # H-154: no degradar al último ADMG activo (dejaría el sistema sin administrador).
        if (u.perfil or "").upper() == "ADMG" and cod != "ADMG" and u.activo and _es_ultimo_admg(db, u.id):
            raise HTTPException(409, "No se puede quitar el rol de administrador al último ADMG activo.")
        u.perfil = cod
    db.commit(); db.refresh(u)
    _audit(db, actor, "Usuario", u.id, "EDITAR", antes=antes,
           despues={"nombre": u.nombre, "perfil": u.perfil}, detalle=f"Edición de usuario {u.username}")
    return u


@router.post("/usuarios/{usuario_id}/baja", response_model=schemas.UsuarioOut)
def baja_usuario(usuario_id: int, db: Session = Depends(get_db),
                 actor: tuple = Depends(_actor),
                 actual: models.Usuario = Depends(get_current_user)):
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if u.id == actual.id:
        raise HTTPException(409, "No podés darte de baja a vos mismo.")
    if (u.perfil or "").upper() == "ADMG" and u.activo:
        otros = db.scalar(select(func.count()).select_from(models.Usuario).where(
            models.Usuario.perfil == "ADMG", models.Usuario.activo.is_(True), models.Usuario.id != u.id))
        if not otros:
            raise HTTPException(409, "No se puede dar de baja al último administrador activo.")
    u.activo = False
    db.commit(); db.refresh(u)
    _audit(db, actor, "Usuario", u.id, "BAJA", detalle=f"Baja de usuario {u.username}")
    return u


@router.post("/usuarios/{usuario_id}/reactivar", response_model=schemas.UsuarioOut)
def reactivar_usuario(usuario_id: int, db: Session = Depends(get_db),
                      actor: tuple = Depends(_actor)):
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    u.activo = True
    db.commit(); db.refresh(u)
    _audit(db, actor, "Usuario", u.id, "REACTIVAR", detalle=f"Reactivación de usuario {u.username}")
    return u


@router.get("/usuarios/{usuario_id}/perfiles")
def usuario_perfiles(usuario_id: int, db: Session = Depends(get_db)):
    """Perfiles del usuario (multi-rol): principal + adicionales."""
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    principal = (u.perfil or "").upper()
    extra = [p for (p,) in db.query(models.UsuarioPerfil.perfil_codigo)
             .filter(models.UsuarioPerfil.usuario_id == u.id).order_by(models.UsuarioPerfil.perfil_codigo).all()]
    return {"principal": principal, "perfiles": sorted({principal, *[e.upper() for e in extra]} - {""})}


class UsuarioPerfilesIn(BaseModel):
    principal: str
    perfiles: list[str]      # todos los perfiles del usuario (incluye el principal)


@router.put("/usuarios/{usuario_id}/perfiles")
def set_usuario_perfiles(usuario_id: int, data: UsuarioPerfilesIn, db: Session = Depends(get_db),
                         actor: tuple = Depends(_actor)):
    """Fija el perfil principal y los adicionales del usuario (multi-rol)."""
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    antes = {"principal": (u.perfil or "").upper()}
    principal = (data.principal or "").strip().upper()
    todos = {p.strip().upper() for p in data.perfiles if p.strip()}
    if not principal:
        raise HTTPException(422, "Debe haber un perfil principal.")
    # H-154: no degradar al último ADMG activo cambiándole el perfil principal.
    if (u.perfil or "").upper() == "ADMG" and principal != "ADMG" and u.activo and _es_ultimo_admg(db, u.id):
        raise HTTPException(409, "No se puede quitar el rol de administrador al último ADMG activo.")
    todos.add(principal)
    u.perfil = principal
    db.query(models.UsuarioPerfil).filter_by(usuario_id=u.id).delete()
    for cod in (todos - {principal}):
        db.add(models.UsuarioPerfil(usuario_id=u.id, perfil_codigo=cod))
    db.commit()
    _audit(db, actor, "Usuario", u.id, "PERFILES", antes=antes,
           despues={"principal": principal, "perfiles": sorted(todos)},
           detalle=f"Roles de {u.username}: principal {principal}")
    return {"principal": principal, "perfiles": sorted(todos)}


# ─────────── Grupos (bundle de roles) ───────────
@router.get("/grupos")
def grupos(db: Session = Depends(get_db)):
    roles_por: dict[str, list[str]] = {}
    for gr in db.query(models.GrupoRol).all():
        roles_por.setdefault(gr.grupo_codigo, []).append(gr.rol_codigo)
    miembros = dict(db.execute(select(models.UsuarioGrupo.grupo_codigo, func.count())
                               .group_by(models.UsuarioGrupo.grupo_codigo)).all())
    return [{"id": g.id, "codigo": g.codigo, "nombre": g.nombre, "activo": g.activo,
             "roles": sorted(roles_por.get(g.codigo, [])), "miembros": miembros.get(g.codigo, 0)}
            for g in db.scalars(select(models.Grupo).order_by(models.Grupo.codigo)).all()]


class GrupoIn(BaseModel):
    codigo: str = ""
    nombre: str = ""
    activo: bool = True


@router.post("/grupos", status_code=201)
def crear_grupo(data: GrupoIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    cod = data.codigo.strip().upper()
    if not cod:
        raise HTTPException(422, "El código es obligatorio.")
    if len(cod) > 12:
        raise HTTPException(422, "El código no puede superar los 12 caracteres.")
    if db.scalar(select(models.Grupo).where(models.Grupo.codigo == cod)):
        raise HTTPException(409, "Ya existe un grupo con ese código.")
    g = models.Grupo(codigo=cod, nombre=data.nombre.strip(), activo=data.activo)
    db.add(g); _commit_unico(db, "Ya existe un grupo con ese código."); db.refresh(g)
    _audit(db, actor, "Grupo", g.codigo, "CREAR", despues={"codigo": g.codigo, "nombre": g.nombre},
           detalle=f"Alta de grupo {g.codigo}")
    return {"id": g.id, "codigo": g.codigo, "nombre": g.nombre, "activo": g.activo, "roles": [], "miembros": 0}


@router.put("/grupos/{grupo_id}")
def editar_grupo(grupo_id: int, data: GrupoIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    g = db.get(models.Grupo, grupo_id)
    if not g:
        raise HTTPException(404, "Grupo no encontrado")
    antes = {"nombre": g.nombre, "activo": g.activo}
    g.nombre = data.nombre.strip(); g.activo = data.activo
    db.commit()
    _audit(db, actor, "Grupo", g.codigo, "EDITAR", antes=antes,
           despues={"nombre": g.nombre, "activo": g.activo},
           detalle=f"Edición de grupo {g.codigo}" + ("" if g.activo else " (DESACTIVADO)"))
    return {"ok": True}


@router.delete("/grupos/{grupo_id}")
def borrar_grupo(grupo_id: int, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    g = db.get(models.Grupo, grupo_id)
    if not g:
        raise HTTPException(404, "Grupo no encontrado")
    en_uso = db.scalar(select(func.count()).select_from(models.UsuarioGrupo).where(models.UsuarioGrupo.grupo_codigo == g.codigo))
    if en_uso:
        raise HTTPException(409, f"No se puede borrar: {en_uso} usuario(s) pertenecen al grupo.")
    codigo = g.codigo
    db.query(models.GrupoRol).filter_by(grupo_codigo=g.codigo).delete()
    db.delete(g); db.commit()
    _audit(db, actor, "Grupo", codigo, "BORRAR", detalle=f"Baja de grupo {codigo}")
    return {"ok": True}


class GrupoRolesIn(BaseModel):
    roles: list[str]


@router.put("/grupos/{grupo_id}/roles")
def set_grupo_roles(grupo_id: int, data: GrupoRolesIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    g = db.get(models.Grupo, grupo_id)
    if not g:
        raise HTTPException(404, "Grupo no encontrado")
    antes = sorted(x.rol_codigo for x in db.query(models.GrupoRol).filter_by(grupo_codigo=g.codigo).all())
    db.query(models.GrupoRol).filter_by(grupo_codigo=g.codigo).delete()
    nuevos = {x.strip().upper() for x in data.roles if x.strip()}
    for r in nuevos:
        db.add(models.GrupoRol(grupo_codigo=g.codigo, rol_codigo=r))
    db.commit()
    _audit(db, actor, "Grupo", g.codigo, "ROLES", antes={"roles": antes}, despues={"roles": sorted(nuevos)},
           detalle=f"Roles del grupo {g.codigo}: {', '.join(sorted(nuevos)) or '(ninguno)'}")
    return {"ok": True}


# ─────────── Accesos del usuario (roles directos, grupos, permisos directos) con vigencia ───────────
from datetime import date as _date


@router.get("/usuarios/{usuario_id}/accesos")
def usuario_accesos(usuario_id: int, db: Session = Depends(get_db)):
    from app.core.permisos import permisos_efectivos, roles_de, sin_restricciones
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    def _f(x): return str(x) if x else None
    rolesd = [{"codigo": r.perfil_codigo, "desde": _f(r.vigente_desde), "hasta": _f(r.vigente_hasta)}
              for r in db.query(models.UsuarioPerfil).filter_by(usuario_id=u.id).all()]
    grps = [{"codigo": g.grupo_codigo, "desde": _f(g.vigente_desde), "hasta": _f(g.vigente_hasta)}
            for g in db.query(models.UsuarioGrupo).filter_by(usuario_id=u.id).all()]
    directos = [{"ruta": p.ruta, "nivel": p.nivel, "desde": _f(p.vigente_desde), "hasta": _f(p.vigente_hasta)}
                for p in db.query(models.UsuarioPermiso).filter_by(usuario_id=u.id).all()]
    sr = sin_restricciones(db, u)
    return {"principal": (u.perfil or "").upper(), "rolesDirectos": rolesd, "grupos": grps,
            "permisosDirectos": directos, "rolesEfectivos": sorted(roles_de(db, u)),
            "sinRestricciones": sr, "accesoEfectivo": {} if sr else permisos_efectivos(db, u)}


class GrupoAsigIn(BaseModel):
    grupo: str
    desde: _date | None = None
    hasta: _date | None = None


@router.post("/usuarios/{usuario_id}/grupos")
def asignar_grupo(usuario_id: int, data: GrupoAsigIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    cod = data.grupo.strip().upper()
    if not db.scalar(select(models.Grupo).where(models.Grupo.codigo == cod)):
        raise HTTPException(404, "Grupo inexistente.")
    if data.desde and data.hasta and data.hasta < data.desde:
        raise HTTPException(422, "La fecha 'hasta' no puede ser anterior a 'desde'.")
    fila = db.query(models.UsuarioGrupo).filter_by(usuario_id=u.id, grupo_codigo=cod).first()
    if fila:
        fila.vigente_desde = data.desde; fila.vigente_hasta = data.hasta
    else:
        db.add(models.UsuarioGrupo(usuario_id=u.id, grupo_codigo=cod, vigente_desde=data.desde, vigente_hasta=data.hasta))
    db.commit()
    _audit(db, actor, "Usuario", u.id, "GRUPO+",
           despues={"grupo": cod, "desde": str(data.desde or ""), "hasta": str(data.hasta or "")},
           detalle=f"{u.username} agregado al grupo {cod}")
    return {"ok": True}


@router.delete("/usuarios/{usuario_id}/grupos/{grupo_codigo}")
def quitar_grupo(usuario_id: int, grupo_codigo: str, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    fila = db.query(models.UsuarioGrupo).filter_by(usuario_id=usuario_id, grupo_codigo=grupo_codigo.upper()).first()
    if fila:
        db.delete(fila); db.commit()
        _audit(db, actor, "Usuario", usuario_id, "GRUPO-", antes={"grupo": grupo_codigo.upper()},
               detalle=f"Usuario {usuario_id} removido del grupo {grupo_codigo.upper()}")
    return {"ok": True}


# ─────────── Permisos DIRECTOS del usuario (con vigencia) ───────────
class PermisoDirectoIn(BaseModel):
    ruta: str
    nivel: str
    desde: _date | None = None
    hasta: _date | None = None


@router.post("/usuarios/{usuario_id}/permisos-directos")
def asignar_permiso_directo(usuario_id: int, data: PermisoDirectoIn, db: Session = Depends(get_db),
                            actor: tuple = Depends(_actor)):
    """Otorga (o quita, con nivel NINGUNO) un permiso directo sobre una pantalla, con vigencia opcional."""
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    nivel = data.nivel.upper()
    if nivel not in NIVELES_PERMISO:
        raise HTTPException(422, f"Nivel inválido (uno de {NIVELES_PERMISO}).")
    if not data.ruta or not data.ruta.startswith("/") or " " in data.ruta:
        raise HTTPException(422, "Ruta de pantalla inválida.")
    if data.desde and data.hasta and data.hasta < data.desde:
        raise HTTPException(422, "La fecha 'hasta' no puede ser anterior a 'desde'.")
    fila = db.query(models.UsuarioPermiso).filter_by(usuario_id=u.id, ruta=data.ruta).first()
    if nivel == "NINGUNO":
        if fila:
            db.delete(fila)
    elif fila:
        fila.nivel = nivel; fila.vigente_desde = data.desde; fila.vigente_hasta = data.hasta
    else:
        db.add(models.UsuarioPermiso(usuario_id=u.id, ruta=data.ruta, nivel=nivel,
                                     vigente_desde=data.desde, vigente_hasta=data.hasta))
    db.commit()
    _audit(db, actor, "Usuario", u.id, "PERMISO", despues={"ruta": data.ruta, "nivel": nivel},
           detalle=f"Permiso directo {nivel} sobre {data.ruta} a {u.username}")
    return {"ok": True}


@router.delete("/usuarios/{usuario_id}/permisos-directos")
def quitar_permiso_directo(usuario_id: int, ruta: str, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    fila = db.query(models.UsuarioPermiso).filter_by(usuario_id=usuario_id, ruta=ruta).first()
    if fila:
        db.delete(fila); db.commit()
        _audit(db, actor, "Usuario", usuario_id, "PERMISO-", antes={"ruta": ruta},
               detalle=f"Permiso directo sobre {ruta} quitado a usuario {usuario_id}")
    return {"ok": True}


@router.get("/perfiles")
def perfiles(db: Session = Depends(get_db)):
    """Catálogo de perfiles del control de acceso (código → descripción)."""
    return [{"codigo": k, "descripcion": v} for k, v in PERFILES.items()]


@router.get("/perfiles-usados")
def perfiles_usados(db: Session = Depends(get_db)):
    """Códigos de perfil realmente asignados a usuarios (para el datalist del ABM)."""
    rows = db.execute(select(models.Usuario.perfil, func.count()).group_by(models.Usuario.perfil)
                      .order_by(func.count().desc())).all()
    return [{"perfil": p, "usuarios": n} for p, n in rows if p]


class PerfilIn(BaseModel):
    codigo: str = ""
    denominacion: str = ""
    habilitado: bool = True


@router.get("/perfiles-maestro")
def perfiles_maestro(db: Session = Depends(get_db)):
    """Maestro de roles (VFP: maeperfil). El uso cuenta usuarios que lo tienen como
    rol principal O como rol adicional (multi-rol); ambos conjuntos son disjuntos."""
    uso = dict(db.execute(select(models.Usuario.perfil, func.count()).group_by(models.Usuario.perfil)).all())
    extra = dict(db.execute(select(models.UsuarioPerfil.perfil_codigo,
                                   func.count(func.distinct(models.UsuarioPerfil.usuario_id)))
                            .group_by(models.UsuarioPerfil.perfil_codigo)).all())
    return [{"id": p.id, "codigo": p.codigo, "denominacion": p.denominacion,
             "habilitado": p.habilitado, "usuarios": uso.get(p.codigo, 0) + extra.get(p.codigo, 0)}
            for p in db.scalars(select(models.Perfil).order_by(models.Perfil.codigo)).all()]


@router.post("/perfiles-maestro", status_code=201)
def crear_perfil(data: PerfilIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    cod = data.codigo.strip().upper()
    if not cod:
        raise HTTPException(422, "El código es obligatorio.")
    if len(cod) > 6:
        raise HTTPException(422, "El código no puede superar los 6 caracteres.")
    if db.scalar(select(models.Perfil).where(models.Perfil.codigo == cod)):
        raise HTTPException(409, "Ya existe un perfil con ese código.")
    p = models.Perfil(codigo=cod, denominacion=data.denominacion.strip(), habilitado=data.habilitado)
    db.add(p); _commit_unico(db, "Ya existe un rol con ese código."); db.refresh(p)
    _audit(db, actor, "Rol", p.codigo, "CREAR", despues={"codigo": p.codigo, "denominacion": p.denominacion},
           detalle=f"Alta de rol {p.codigo}")
    return {"id": p.id, "codigo": p.codigo, "denominacion": p.denominacion, "habilitado": p.habilitado, "usuarios": 0}


@router.put("/perfiles-maestro/{perfil_id}")
def editar_perfil(perfil_id: int, data: PerfilIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    p = db.get(models.Perfil, perfil_id)
    if not p:
        raise HTTPException(404, "Perfil no encontrado")
    # H-154: no deshabilitar el rol ADMG (auth.py bloquea el login de todos los ADMG si el rol está deshabilitado).
    if (p.codigo or "").upper() == "ADMG" and not data.habilitado:
        raise HTTPException(409, "No se puede deshabilitar el rol de administrador (ADMG).")
    antes = {"denominacion": p.denominacion, "habilitado": p.habilitado}
    p.denominacion = data.denominacion.strip()
    p.habilitado = data.habilitado
    db.commit(); db.refresh(p)
    _audit(db, actor, "Rol", p.codigo, "EDITAR", antes=antes,
           despues={"denominacion": p.denominacion, "habilitado": p.habilitado}, detalle=f"Edición de rol {p.codigo}")
    return {"id": p.id, "codigo": p.codigo, "denominacion": p.denominacion, "habilitado": p.habilitado}


@router.delete("/perfiles-maestro/{perfil_id}")
def borrar_perfil(perfil_id: int, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    p = db.get(models.Perfil, perfil_id)
    if not p:
        raise HTTPException(404, "Perfil no encontrado")
    como_principal = db.scalar(select(func.count()).select_from(models.Usuario).where(models.Usuario.perfil == p.codigo))
    como_adicional = db.scalar(select(func.count(func.distinct(models.UsuarioPerfil.usuario_id)))
                               .where(models.UsuarioPerfil.perfil_codigo == p.codigo))
    en_uso = (como_principal or 0) + (como_adicional or 0)
    if en_uso:
        raise HTTPException(409, f"No se puede borrar: {en_uso} usuario(s) tienen el rol {p.codigo}.")
    en_grupo = db.scalar(select(func.count()).select_from(models.GrupoRol).where(models.GrupoRol.rol_codigo == p.codigo))
    if en_grupo:
        raise HTTPException(409, f"No se puede borrar: {en_grupo} grupo(s) incluyen el rol {p.codigo}.")
    codigo = p.codigo
    db.query(models.PerfilPermiso).filter_by(perfil_codigo=p.codigo).delete()
    db.delete(p); db.commit()
    _audit(db, actor, "Rol", codigo, "BORRAR", detalle=f"Baja de rol {codigo}")
    return {"ok": True}


# ---- Permisos por pantalla (RBAC del perfil) ----
NIVELES_PERMISO = ["NINGUNO", "CONSULTA", "ESCRITURA", "TOTAL"]


def _perfil_or_404(db: Session, perfil_id: int) -> models.Perfil:
    p = db.get(models.Perfil, perfil_id)
    if not p:
        raise HTTPException(404, "Perfil no encontrado")
    return p


@router.get("/perfiles-maestro/{perfil_id}/permisos")
def perfil_permisos(perfil_id: int, db: Session = Depends(get_db)):
    """Mapa { ruta: nivel } de los permisos del perfil (rutas ausentes = NINGUNO)."""
    p = _perfil_or_404(db, perfil_id)
    filas = db.query(models.PerfilPermiso).filter_by(perfil_codigo=p.codigo).all()
    return {"codigo": p.codigo, "niveles": NIVELES_PERMISO,
            "permisos": {f.ruta: f.nivel for f in filas}}


class PermisoIn(BaseModel):
    ruta: str
    nivel: str


@router.put("/perfiles-maestro/{perfil_id}/permisos")
def set_perfil_permiso(perfil_id: int, data: PermisoIn, db: Session = Depends(get_db), actor: tuple = Depends(_actor)):
    """Fija el nivel de una pantalla para el perfil. NINGUNO borra la fila."""
    p = _perfil_or_404(db, perfil_id)
    nivel = data.nivel.upper()
    if nivel not in NIVELES_PERMISO:
        raise HTTPException(422, f"Nivel inválido (uno de {NIVELES_PERMISO}).")
    if not data.ruta or not data.ruta.startswith("/") or " " in data.ruta:
        raise HTTPException(422, "Ruta de pantalla inválida.")
    fila = db.query(models.PerfilPermiso).filter_by(perfil_codigo=p.codigo, ruta=data.ruta).first()
    if nivel == "NINGUNO":
        if fila:
            db.delete(fila)
    elif fila:
        fila.nivel = nivel
    else:
        db.add(models.PerfilPermiso(perfil_codigo=p.codigo, ruta=data.ruta, nivel=nivel))
    db.commit()
    _audit(db, actor, "Rol", p.codigo, "PERMISO", despues={"ruta": data.ruta, "nivel": nivel},
           detalle=f"Permiso {nivel} sobre {data.ruta} para el rol {p.codigo}")
    return {"ok": True, "ruta": data.ruta, "nivel": nivel}


class PermisosBulkIn(BaseModel):
    rutas: list[str]
    nivel: str


@router.put("/perfiles-maestro/{perfil_id}/permisos-bulk")
def set_perfil_permisos_bulk(perfil_id: int, data: PermisosBulkIn, db: Session = Depends(get_db),
                             actor: tuple = Depends(_actor)):
    """Aplica un nivel a varias pantallas de una (p.ej. todo un módulo)."""
    p = _perfil_or_404(db, perfil_id)
    nivel = data.nivel.upper()
    if nivel not in NIVELES_PERMISO:
        raise HTTPException(422, f"Nivel inválido (uno de {NIVELES_PERMISO}).")
    existentes = {f.ruta: f for f in db.query(models.PerfilPermiso).filter_by(perfil_codigo=p.codigo).all()}
    for ruta in data.rutas:
        fila = existentes.get(ruta)
        if nivel == "NINGUNO":
            if fila:
                db.delete(fila)
        elif fila:
            fila.nivel = nivel
        else:
            db.add(models.PerfilPermiso(perfil_codigo=p.codigo, ruta=ruta, nivel=nivel))
    db.commit()
    _audit(db, actor, "Rol", p.codigo, "PERMISO-BULK", despues={"nivel": nivel, "rutas": len(data.rutas)},
           detalle=f"Permiso {nivel} sobre {len(data.rutas)} pantalla(s) del rol {p.codigo}")
    return {"ok": True, "actualizadas": len(data.rutas), "nivel": nivel}


# ---- Usuarios asignados al perfil ----
@router.get("/perfiles-maestro/{perfil_id}/usuarios")
def perfil_usuarios(perfil_id: int, db: Session = Depends(get_db)):
    """Miembros del rol: usuarios que lo tienen como principal o como rol adicional."""
    p = _perfil_or_404(db, perfil_id)
    extra_ids = {r[0] for r in db.query(models.UsuarioPerfil.usuario_id)
                 .filter_by(perfil_codigo=p.codigo).all()}
    us = db.scalars(select(models.Usuario).where(
        (models.Usuario.perfil == p.codigo) | (models.Usuario.id.in_(extra_ids)))
        .order_by(models.Usuario.username)).all()
    return {"codigo": p.codigo,
            "usuarios": [{"id": u.id, "username": u.username, "nombre": u.nombre, "activo": u.activo,
                          "principal": (u.perfil or "").upper() == p.codigo} for u in us]}


class AsignarUsuariosIn(BaseModel):
    usuario_ids: list[int]


@router.post("/perfiles-maestro/{perfil_id}/usuarios")
def asignar_usuarios(perfil_id: int, data: AsignarUsuariosIn, db: Session = Depends(get_db),
                     actor: tuple = Depends(_actor)):
    """Suma este rol a los usuarios indicados como rol ADICIONAL (multi-rol), sin pisar su
    rol principal. Si el usuario ya lo tiene (principal o adicional), no hace nada."""
    p = _perfil_or_404(db, perfil_id)
    n = 0
    for uid in data.usuario_ids:
        u = db.get(models.Usuario, uid)
        if not u or (u.perfil or "").upper() == p.codigo:
            continue
        if db.query(models.UsuarioPerfil).filter_by(usuario_id=u.id, perfil_codigo=p.codigo).first():
            continue
        db.add(models.UsuarioPerfil(usuario_id=u.id, perfil_codigo=p.codigo)); n += 1
    db.commit()
    _audit(db, actor, "Rol", p.codigo, "ASIGNAR", despues={"asignados": n},
           detalle=f"Rol {p.codigo} asignado a {n} usuario(s)")
    return {"ok": True, "asignados": n, "codigo": p.codigo}


@router.get("/auditoria")
def auditoria(
    usuario: str | None = None,
    desde: __import__("datetime").date | None = None,
    hasta: __import__("datetime").date | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Consulta paginada del log de auditoría (VFP: auditoria, rpt106auditoria)."""
    from app.services.auditoria import consultar
    return consultar(db, usuario=usuario, desde=desde, hasta=hasta,
                     limit=min(limit, 200), offset=offset)


@router.get("/auditoria/resumen")
def auditoria_resumen(
    por: str = "usuario",
    desde: __import__("datetime").date | None = None,
    hasta: __import__("datetime").date | None = None,
    db: Session = Depends(get_db),
):
    """Auditoría agrupada por usuario (X3005) o por máquina (X3010)."""
    from app.services.auditoria import resumen
    return resumen(db, por=("maquina" if por == "maquina" else "usuario"),
                   desde=desde, hasta=hasta)


# ---------------- Auditoría de cambios (sistema nuevo: antes/después + IP) ----------------
@router.get("/auditoria-cambios")
def auditoria_cambios(
    texto: str | None = None,
    entidad: str | None = None,
    operacion: str | None = None,
    resultado: str | None = None,
    desde: __import__("datetime").date | None = None,
    hasta: __import__("datetime").date | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Rastro de mutaciones del sistema nuevo (quién cambió qué, con diff e IP)."""
    from app.services.auditoria import consultar_cambios
    return consultar_cambios(db, texto=texto, entidad=entidad, operacion=operacion,
                             resultado=resultado, desde=desde, hasta=hasta,
                             limit=min(limit, 200), offset=offset)


@router.get("/auditoria-cambios/{cambio_id}")
def auditoria_cambio_detalle(cambio_id: int, db: Session = Depends(get_db)):
    """Detalle de un evento con el diff antes/después completo."""
    from app.services.auditoria import obtener_cambio
    ev = obtener_cambio(db, cambio_id)
    if not ev:
        raise HTTPException(404, "Evento de auditoría no encontrado")
    return ev


# ---------------- Requisitos de crédito ----------------
@router.get("/requisitos", response_model=list[schemas.RequisitoOut])
def requisitos(db: Session = Depends(get_db)):
    return db.scalars(select(models.Requisito).order_by(models.Requisito.id)).all()


@router.post("/requisitos", response_model=schemas.RequisitoOut, status_code=201)
def crear_requisito(data: schemas.RequisitoUpsert, db: Session = Depends(get_db)):
    r = models.Requisito(**data.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r


# ---------------- Gasistas / Institutos ----------------
@router.get("/gasistas", response_model=list[schemas.GasistaOut])
def gasistas(db: Session = Depends(get_db)):
    return db.scalars(select(models.Gasista).order_by(models.Gasista.nombre)).all()


@router.post("/gasistas", response_model=schemas.GasistaOut, status_code=201)
def crear_gasista(data: schemas.GasistaUpsert, db: Session = Depends(get_db)):
    g = models.Gasista(**data.model_dump())
    db.add(g); db.commit(); db.refresh(g)
    return g


# ---------------- Montos máximos por período ----------------
@router.get("/montos-periodo", response_model=list[schemas.MontoPeriodoOut])
def montos_periodo(db: Session = Depends(get_db)):
    return db.scalars(select(models.MontoPeriodo).order_by(
        models.MontoPeriodo.periodo.desc())).all()


@router.post("/montos-periodo", response_model=schemas.MontoPeriodoOut, status_code=201)
def crear_monto_periodo(data: schemas.MontoPeriodoUpsert, db: Session = Depends(get_db)):
    m = models.MontoPeriodo(**data.model_dump())
    db.add(m); db.commit(); db.refresh(m)
    return m
