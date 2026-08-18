from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings


class SettingsRepository:
    """
    Guarda un único documento de configuración (singleton config).
    Patrón: Repository.
    """

    def col(self, db: AsyncIOMotorDatabase):
        return db[settings.SETTINGS_COL]  # agrega SETTINGS_COL en config

    @staticmethod
    def _default_doc() -> Dict[str, Any]:
        return {
            # Debe coincidir con CONFIDENCE_MIN del agente local (0.65). Si el
            # backend filtrara mas alto, descartaria detecciones que el agente
            # si considera validas y que antes quedaban registradas.
            "confidence_threshold": 0.65,
            "auto_alert": True,
            # NO IMPLEMENTADO: no existe envío de correo en el backend.
            # Por defecto en False para no prometer una función inexistente.
            "email_notifications": False,
            "sound_alerts": False,
            "save_evidence": True,
            "max_fps": 30,
            "infer_every_n_frames": 5,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_or_create(self, db: AsyncIOMotorDatabase) -> Dict[str, Any]:
        doc = await self.col(db).find_one({"_id": "global"})
        if doc:
            return doc

        doc = self._default_doc()
        doc["_id"] = "global"
        await self.col(db).insert_one(doc)
        return doc

    async def patch(self, db: AsyncIOMotorDatabase, patch: Dict[str, Any]) -> Dict[str, Any]:
        patch = dict(patch)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()

        await self.col(db).update_one(
            {"_id": "global"},
            {"$set": patch},
            upsert=True,
        )

        return await self.get_or_create(db)


settings_repo = SettingsRepository()