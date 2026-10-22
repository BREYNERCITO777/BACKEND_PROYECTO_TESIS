"""Autenticación JWT y control de acceso por rol."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import get_db

# FastAPI OAuth2 helper:
# tokenUrl debe apuntar al endpoint que entrega el token (tu /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


def create_access_token(*, sub: str, role: str, expires_minutes: Optional[int] = None) -> str:
    """
    Crea JWT con:
      - sub: id del usuario (string)
      - role: rol (admin/operator) (lo incluimos, pero IGUAL validamos en DB)
      - iat/exp: tiempos en epoch
    """
    now = datetime.now(timezone.utc)
    exp_min = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MIN
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_min)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def _unauthorized(detail: str = "No autorizado") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida el JWT (incluye exp).
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError:
        raise _unauthorized("Token inválido o expirado")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """
    1) Decodifica el token
    2) Toma sub (user_id)
    3) Busca en DB el usuario real
    4) Devuelve user sin password_hash y con _id string
    """
    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Token sin 'sub'")

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise _unauthorized("Token sub inválido")

    user = await db[settings.USERS_COL].find_one({"_id": oid})
    if not user:
        raise _unauthorized("Usuario no existe")

    # Normaliza salida
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)

    # ⚠️ Importante: usamos role desde DB (no confiamos en token)
    user["role"] = user.get("role", "operator")

    return user


def require_auth(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependencia: exige una sesión válida y devuelve el usuario."""
    return user


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependencia: exige una sesión de administrador; si no, responde 403."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol admin")
    return user


def require_roles(*allowed: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Uso:
      _user = Depends(require_roles("admin"))
      _user = Depends(require_roles("admin", "operator"))
    """
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos",
            )
        return user

    return _dep