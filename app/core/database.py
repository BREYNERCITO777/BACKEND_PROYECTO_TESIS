"""Conexión única a MongoDB compartida por toda la aplicación."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from fastapi import Depends

class Mongo:
    """Cliente y base de datos de Motor, compartidos por toda la aplicación."""
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo = Mongo()


def connect_db() -> None:
    """Abre la conexión a MongoDB si aún no está abierta."""
    if mongo.client is not None and mongo.db is not None:
        return
    mongo.client = AsyncIOMotorClient(settings.MONGO_URL)
    mongo.db = mongo.client[settings.MONGO_DB]


def close_db() -> None:
    """Cierra la conexión a MongoDB."""
    if mongo.client is not None:
        mongo.client.close()
    mongo.client = None
    mongo.db = None


def get_db() -> AsyncIOMotorDatabase:
    """Dependencia de FastAPI que entrega la base de datos; falla si no hay conexión."""
    if mongo.db is None:
        raise RuntimeError("DB no inicializada")
    return mongo.db
