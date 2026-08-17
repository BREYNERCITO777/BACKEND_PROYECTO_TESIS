from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def allowed_modules_for(role: str) -> list[str]:
    if role == "admin":
        return [
            "dashboard",
            "cameras",
            "incidents",
            "evidence",
            "alerts",
            "settings",
            "users",
        ]
    return [
        "dashboard",
        "incidents",
        "evidence",
        "alerts",
    ]


def _is_inactive(user: dict) -> bool:
    # ✅ estado: 1=activo, 0=inactivo (default activo si no existe)
    try:
        return int(user.get("estado", 1)) == 0
    except Exception:
        return False


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # OAuth2PasswordRequestForm usa: username, password (aunque sea email)
    email = (form.username or "").strip().lower()

    user = await UserRepository(db).get_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # ✅ bloquear login si está inactivo
    if _is_inactive(user):
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    if not verify_password(form.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    role = user.get("role", "operator")
    token = create_access_token(sub=str(user["_id"]), role=role)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "_id": str(user["_id"]),
            "email": user.get("email"),
            "name": user.get("name", ""),
            "role": role,
            "estado": int(user.get("estado", 1)),
        },
        "allowed_modules": allowed_modules_for(role),
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    # ✅ bloquear sesión si quedó inactivo luego
    if _is_inactive(user):
        raise HTTPException(status_code=401, detail="Usuario inactivo")

    role = user.get("role", "operator")
    return {
        "user": {
            "_id": user["_id"],
            "email": user.get("email"),
            "name": user.get("name", ""),
            "role": role,
            "estado": int(user.get("estado", 1)),
        },
        "allowed_modules": allowed_modules_for(role),
    }