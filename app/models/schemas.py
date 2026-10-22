"""Esquemas Pydantic de autenticación."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Datos para registrar un usuario."""
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "operator"  # admin | operator | viewer (ajusta si quieres)


class UserLogin(BaseModel):
    """Credenciales de inicio de sesión."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Usuario tal como lo devuelve la API, sin contraseña."""
    _id: str
    email: EmailStr
    role: str


class TokenOut(BaseModel):
    """Token de sesión devuelto al iniciar sesión."""
    access_token: str
    token_type: str = "bearer"
