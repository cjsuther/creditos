"""Dependencias comunes de FastAPI: sesión de usuario y control de perfil."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class Actor:
    """Quién y desde dónde origina una mutación, para auditoría.

    Autenticación OPCIONAL: no lanza 401 si no hay token (a diferencia de
    get_current_user). Un endpoint sin sesión igual queda auditado como 'anonimo'.
    """
    usuario: str = "anonimo"
    perfil: str = ""
    ip: str = ""


def get_actor(request: Request, db: Session = Depends(get_db)) -> Actor:
    from app.services.auditoria import ip_de
    actor = Actor(ip=ip_de(request))
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth[7:])
            u = db.query(models.Usuario).filter_by(username=payload.get("sub"), activo=True).first()
            if u:
                actor.usuario, actor.perfil = u.username, u.perfil
        except Exception:
            pass
    return actor


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        username = payload.get("sub")
    except InvalidTokenError:
        raise cred_exc
    # Segregación de realms: un token del PORTAL ciudadano jamás abre el backoffice interno.
    if payload.get("scope") == "portal":
        raise cred_exc
    user = db.query(models.Usuario).filter_by(username=username, activo=True).first()
    if not user:
        raise cred_exc
    return user


@dataclass
class Ciudadano:
    """Identidad del portal (autenticada por Mi Catamarca). NO es un Usuario del backoffice."""
    sub: str
    email: str = ""
    nombre: str = ""
    documento: str = ""


def get_ciudadano(request: Request) -> Ciudadano:
    """Auth del PORTAL: exige un token con scope 'portal'. Rechaza tokens internos."""
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión de portal inválida",
                             headers={"WWW-Authenticate": "Bearer"})
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise cred_exc
    try:
        payload = decode_token(auth[7:])
    except InvalidTokenError:
        raise cred_exc
    if payload.get("scope") != "portal":
        raise cred_exc
    return Ciudadano(sub=payload.get("sub", ""), email=payload.get("email", ""),
                     nombre=payload.get("nombre", ""), documento=payload.get("documento", ""))


def requiere_perfil(*prefijos: str):
    """Restringe un endpoint a perfiles cuyo código empieza con alguno de los prefijos.

    Replica el control por perfil de symdeperf. ADMG siempre pasa.
    """
    def checker(user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        p = user.perfil.upper()
        if p == "ADMG" or any(p.startswith(x) or p[1:3] == x for x in prefijos):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Perfil sin acceso a este módulo")
    return checker
