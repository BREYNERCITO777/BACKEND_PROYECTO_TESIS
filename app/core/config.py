from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_PREFIX: str = "/api/v1"

    # YOLO
    MODEL_PATH: str = "app/models/best.pt"

    # Respaldo del umbral de confianza: solo se usa si el documento de
    # configuracion aun no existe en Mongo. El valor real vive en /settings.
    # Alineado con CONFIDENCE_MIN del agente local (0.65).
    CONF_TH: float = 0.65

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

    # Clave con la que se cifran las URL RTSP de las cámaras antes de
    # guardarlas en Mongo, porque llevan usuario y contraseña. Si se deja
    # vacía se usa JWT_SECRET, para no obligar a configurar otra variable.
    RTSP_SECRET_KEY: str = ""

    # Token compartido con el agente YOLO local (POST /agent/detections).
    # Sin valor por defecto a propósito: si falta en el .env la app NO arranca
    # (ver app/core/lifecycle.py). Nunca hardcodear un token de respaldo aquí.
    AGENT_TOKEN: str = ""

    # Segundos mínimos entre dos detecciones aceptadas de la misma cámara.
    # Evita que un agente detectando a N fps genere N incidentes por segundo.
    # 0 desactiva el control.
    AGENT_COOLDOWN_SECONDS: float = 5.0

    # Tamaño máximo de la evidencia base64 que acepta el agente. Mongo rechaza
    # documentos de más de 16 MB, así que el límite debe quedar por debajo.
    AGENT_MAX_EVIDENCE_MB: float = 4.0

    # Desde qué direcciones puede llamar el navegador. En el .env se escriben
    # separadas por comas:
    #
    #     CORS_ORIGINS=http://localhost:5173,http://192.168.10.20:5173
    #
    # Se declara como TEXTO a propósito, no como List[str]. Con una lista,
    # pydantic-settings intenta interpretar la variable como JSON *antes* de
    # que corra ningún validador, y el formato separado por comas —el que
    # documentamos— aborta el arranque con "error parsing value for field
    # CORS_ORIGINS". El backend no llegaba ni a levantar.
    #
    # Para leer la lista ya resuelta, usar la propiedad cors_origins.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        """Las direcciones permitidas, ya separadas.

        Acepta el formato separado por comas y también una lista JSON, porque
        algunos paneles de despliegue escriben la variable de esa forma.
        """
        texto = (self.CORS_ORIGINS or "").strip()
        if not texto:
            return ["http://localhost:3000"]

        if texto.startswith("[") and texto.endswith("]"):
            try:
                import json

                valores = json.loads(texto)
                if isinstance(valores, list):
                    limpias = [str(x).strip() for x in valores if str(x).strip()]
                    if limpias:
                        return limpias
            except Exception:
                pass

        limpias = [x.strip() for x in texto.split(",") if x.strip()]
        return limpias or ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
