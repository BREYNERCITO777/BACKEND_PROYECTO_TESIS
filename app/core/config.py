from __future__ import annotations

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_PREFIX: str = "/api/v1"

    # YOLO
    MODEL_PATH: str = "app/models/best.pt"
    CONF_TH: float = 0.5

    # Mongo
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB: str = "sistema_armas"
    INCIDENTS_COL: str = "incidents"
    CAMERAS_COL: str = "cameras"
    USERS_COL: str = "users"
    ALERTS_COL: str = "alerts"
    SETTINGS_COL: str = "settings"

    # Static / evidencias
    STATIC_DIR: str = "app/static"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Auth / JWT
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MIN: int = 60 * 24  # 24h

    # Token compartido con el agente YOLO local (POST /agent/detections).
    # Sin valor por defecto a propósito: si falta en el .env la app NO arranca
    # (ver app/core/lifecycle.py). Nunca hardcodear un token de respaldo aquí.
    AGENT_TOKEN: str = ""

    # CORS (en .env usar CSV: http://localhost:3000,http://127.0.0.1:3000)
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if v is None:
            return ["http://localhost:3000"]

        if isinstance(v, list):
            return v

        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["http://localhost:3000"]

            # JSON string: ["a","b"]
            if s.startswith("[") and s.endswith("]"):
                try:
                    import json
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass

            # CSV
            return [x.strip() for x in s.split(",") if x.strip()]

        return ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
