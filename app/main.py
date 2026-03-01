from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.lifecycle import lifespan

from app.routers.settings import router as settings_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.inference import router as inference_router
from app.routers.incidents import router as incidents_router
from app.routers.alerts import router as alerts_router
from app.routers.cameras import router as cameras_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Sentinel AI Backend",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Estado global para streams activos
    app.state.active_streams = {}

    # --- CONFIGURACIÓN DE CORS SOLUCIONADA ---
    # Aquí definimos explícitamente quiénes pueden conectarse
    origenes_permitidos = [
        "https://fronted-proyecto-tesis.vercel.app",  # Tu frontend en Vercel
        "http://localhost:5173",                      # Por si pruebas localmente con Vite
        "http://localhost:3000",                      # Por si pruebas localmente
        "http://127.0.0.1:5173"
    ]
    
    # Mantenemos también los que ya tenías en tu config por si acaso
    if isinstance(settings.CORS_ORIGINS, list):
        origenes_permitidos.extend(settings.CORS_ORIGINS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes_permitidos, # Inyectamos la lista aquí
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Servir evidencias por /static/...
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

    api_prefix = settings.API_PREFIX  # ej: /api/v1

    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(inference_router, prefix=api_prefix)
    app.include_router(incidents_router, prefix=api_prefix)
    app.include_router(alerts_router, prefix=api_prefix)
    app.include_router(cameras_router, prefix=api_prefix)
    app.include_router(settings_router, prefix=api_prefix)
    
    @app.get("/", tags=["default"])
    def root():
        return {"status": "ok", "name": "Sentinel AI Backend"}

    return app

app = create_app()