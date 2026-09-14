"""Enforcement del RBAC por pantalla (perfil × ruta → nivel).

Reglas de seguridad para no bloquear el sistema al activar el control:
- El perfil **ADMG** siempre tiene acceso total.
- Un perfil **sin ninguna fila de permisos** se considera "no configurado" → sin restricciones
  (comportamiento legacy). Recién cuando el perfil tiene ≥1 permiso cargado, se enforca: sólo las
  pantallas configuradas, en su nivel; el resto es NINGUNO.

Niveles ordenados: NINGUNO < CONSULTA < ESCRITURA < TOTAL.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app import models

ORDEN = {"NINGUNO": 0, "CONSULTA": 1, "ESCRITURA": 2, "TOTAL": 3}


from datetime import date


def _perfil(user: models.Usuario) -> str:
    return (user.perfil or "").upper()


def _vig(desde, hasta, hoy: date) -> bool:
    return (desde is None or desde <= hoy) and (hasta is None or hoy <= hasta)


def roles_de(db: Session, user: models.Usuario, hoy: date | None = None) -> set[str]:
    """Roles efectivos del usuario (modelo IAM), considerando vigencia:
    rol principal + roles directos (usuario_perfil) vigentes + roles heredados de sus grupos vigentes."""
    hoy = hoy or date.today()
    roles = {_perfil(user)}
    for ur in db.query(models.UsuarioPerfil).filter_by(usuario_id=user.id).all():
        if _vig(ur.vigente_desde, ur.vigente_hasta, hoy):
            roles.add((ur.perfil_codigo or "").upper())
    grupos = [ug.grupo_codigo for ug in db.query(models.UsuarioGrupo).filter_by(usuario_id=user.id).all()
              if _vig(ug.vigente_desde, ug.vigente_hasta, hoy)]
    if grupos:
        # Un grupo DESACTIVADo (activo=False) no otorga sus roles: desactivar el grupo corta el acceso de
        # todos sus miembros de una (no hay que quitar la membresía uno por uno). H-153.
        activos = {c for (c,) in db.query(models.Grupo.codigo).filter(
            models.Grupo.codigo.in_(grupos), models.Grupo.activo.is_(True)).all()}
        if activos:
            for gr in db.query(models.GrupoRol).filter(models.GrupoRol.grupo_codigo.in_(activos)).all():
                roles.add((gr.rol_codigo or "").upper())
    return {r for r in roles if r}


# Alias de compatibilidad (código previo llamaba perfiles_de).
def perfiles_de(db: Session, user: models.Usuario) -> set[str]:
    return roles_de(db, user)


def _permisos_directos(db: Session, user: models.Usuario, hoy: date) -> dict[str, str]:
    """{ ruta: nivel } de los permisos DIRECTOS del usuario que estén vigentes."""
    out: dict[str, str] = {}
    for up in db.query(models.UsuarioPermiso).filter_by(usuario_id=user.id).all():
        if _vig(up.vigente_desde, up.vigente_hasta, hoy):
            if ORDEN[up.nivel] > ORDEN[out.get(up.ruta, "NINGUNO")]:
                out[up.ruta] = up.nivel
    return out


def sin_restricciones(db: Session, user: models.Usuario) -> bool:
    roles = roles_de(db, user)
    if "ADMG" in roles:
        return True
    hay_rol_cfg = db.query(models.PerfilPermiso).filter(models.PerfilPermiso.perfil_codigo.in_(roles)).count() > 0
    hay_perm_dir = bool(_permisos_directos(db, user, date.today()))
    return not (hay_rol_cfg or hay_perm_dir)


def nivel_efectivo(db: Session, user: models.Usuario, ruta: str) -> str:
    if sin_restricciones(db, user):
        return "TOTAL"
    hoy = date.today()
    niveles = [f.nivel for f in db.query(models.PerfilPermiso).filter(
        models.PerfilPermiso.perfil_codigo.in_(roles_de(db, user, hoy)),
        models.PerfilPermiso.ruta == ruta).all()]
    directo = _permisos_directos(db, user, hoy).get(ruta)
    if directo:
        niveles.append(directo)
    return max(niveles, key=lambda n: ORDEN[n], default="NINGUNO")


def permisos_efectivos(db: Session, user: models.Usuario) -> dict[str, str]:
    """Mapa { ruta: nivel } efectivo (unión de roles + grupos + permisos directos, con vigencia)."""
    hoy = date.today()
    out: dict[str, str] = {}
    for f in db.query(models.PerfilPermiso).filter(
            models.PerfilPermiso.perfil_codigo.in_(roles_de(db, user, hoy))).all():
        if f.ruta not in out or ORDEN[f.nivel] > ORDEN[out[f.ruta]]:
            out[f.ruta] = f.nivel
    for ruta, nivel in _permisos_directos(db, user, hoy).items():
        if ruta not in out or ORDEN[nivel] > ORDEN[out[ruta]]:
            out[ruta] = nivel
    return out


# ---- Capacidades del circuito de créditos, derivadas de los ROLES efectivos (H-150) ----
# "Quién puede diseñar / aprobar" se define con roles y grupos (no con overrides ni chequeos por perfil
# principal): para habilitar a alguien se le asigna el rol o el grupo en Seguridad. `roles_de` ya incluye
# el perfil principal + los roles directos + los heredados de los grupos, así que un usuario que pertenece
# a un grupo aprobador puede aprobar aunque su perfil principal no lo sea.
ROLES_EDITA_CREDITOS = {"ADMG", "XCR", "OPER", "SUPE"}    # diseñar/editar/enviar a revisión
ROLES_APRUEBA_CREDITOS = {"ADMG", "SUPE"}                 # aprobar/publicar (cierra el cuatro-ojos)


def caps_creditos(db: Session, user: models.Usuario) -> dict:
    """Capacidades del usuario en el circuito de créditos: {edita, aprueba}, según sus roles efectivos."""
    roles = roles_de(db, user)
    return {"edita": bool(roles & ROLES_EDITA_CREDITOS),
            "aprueba": bool(roles & ROLES_APRUEBA_CREDITOS)}


def requiere_permiso(ruta: str, minimo: str = "CONSULTA"):
    """Dependencia FastAPI: exige que el usuario tenga al menos `minimo` sobre la pantalla `ruta`."""
    def dep(db: Session = Depends(get_db), user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if ORDEN[nivel_efectivo(db, user, ruta)] < ORDEN[minimo]:
            raise HTTPException(403, f"Tu perfil no tiene permiso de {minimo.lower()} sobre esta pantalla.")
        return user
    return dep
