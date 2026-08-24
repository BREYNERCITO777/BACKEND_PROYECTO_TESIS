from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.lifecycle import lifespan

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.inference import router as inference_router
from app.routers.incidents import router as incidents_router
from app.routers.alerts import router as alerts_router
from app.routers.cameras import router as cameras_router
from app.routers.settings import router as settings_router
from app.routers.agent import router as agent_router
from app.routers.ws import router as ws_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sentinel AI Backend",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.state.active_streams = {}

    origenes_permitidos = [
        "https://fronted-proyecto-tesis.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Las que se añadan por configuración, sin repetir las de arriba.
    for origen in settings.cors_origins:
        if origen not in origenes_permitidos:
            origenes_permitidos.append(origen)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes_permitidos,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    os.makedirs(settings.STATIC_DIR, exist_ok=True)

    app.mount(
        "/static",
        StaticFiles(directory=settings.STATIC_DIR),
        name="static",
    )

    api_prefix = settings.API_PREFIX

    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(inference_router, prefix=api_prefix)
    app.include_router(incidents_router, prefix=api_prefix)
    app.include_router(alerts_router, prefix=api_prefix)
    app.include_router(cameras_router, prefix=api_prefix)
    app.include_router(settings_router, prefix=api_prefix)
    app.include_router(agent_router, prefix=api_prefix)
    app.include_router(ws_router, prefix=api_prefix)

    @app.get("/", tags=["default"])
    def root():
        return {
            "status": "ok",
            "name": "Sentinel AI Backend",
            "version": "1.0.0",
        }

    return app


app = create_app()
