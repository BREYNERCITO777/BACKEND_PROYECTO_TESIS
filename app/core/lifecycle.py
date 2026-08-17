from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from ultralytics import YOLO

from app.core.database import mongo, connect_db, close_db
from app.core.config import settings
from app.repositories.incident_repository import IncidentRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Falla temprano y ruidosamente: sin AGENT_TOKEN el endpoint /agent/detections
    # quedaría sin una credencial válida con la cual comparar.
    if not settings.AGENT_TOKEN.strip():
        raise RuntimeError(
            "AGENT_TOKEN no está configurado. Defínelo en el archivo .env "
            "(o como variable de entorno) antes de iniciar el backend."
        )

    connect_db()

    if mongo.db is not None:
        await mongo.db[settings.USERS_COL].create_index("email", unique=True)
        await mongo.db[settings.CAMERAS_COL].create_index("rtsp_url", unique=True)

        # índices de incidentes
        await IncidentRepository(mongo.db).ensure_indexes()

    app.state.yolo_model = YOLO(settings.MODEL_PATH)

    yield

    close_db()
