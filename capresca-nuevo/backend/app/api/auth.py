"""Autenticación: login que emite JWT. Reemplaza el login VFP (formularios\\login)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.deps import get_current_user
from app import models, schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/mis-permisos")
def mis_permisos(db: Session = Depends(get_db), user: models.Usuario = Depends(get_current_user)):
    """Permisos efectivos del usuario logueado, para gatear menú/pantallas/acciones en el front.
    `sinRestricciones` = ADMG o perfil sin RBAC configurado (ve todo)."""
    from app.core.permisos import sin_restricciones, roles_de, permisos_efectivos
    roles = sorted(roles_de(db, user))
    if sin_restricciones(db, user):
        return {"perfil": (user.perfil or "").upper(), "perfiles": roles, "roles": roles,
                "sinRestricciones": True, "permisos": {}}
    return {"perfil": (user.perfil or "").upper(), "perfiles": roles, "roles": roles,
            "sinRestricciones": False, "permisos": permisos_efectivos(db, user)}


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter_by(username=form.username, activo=True).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña inválidos")
    # Perfil deshabilitado en el maestro (maeperfil) → sin acceso.
    pf = db.query(models.Perfil).filter_by(codigo=(user.perfil or "").upper()).first()
    if pf is not None and not pf.habilitado:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu perfil está deshabilitado. Contactá a un administrador.")
    from app.services.auditoria import registrar
    registrar(db, usuario=user.username, proceso="LOGIN", opcion="Ingreso al sistema",
              perfil=user.perfil)
    token = create_access_token(user.username, user.perfil)
    return schemas.Token(access_token=token, perfil=user.perfil, nombre=user.nombre)
