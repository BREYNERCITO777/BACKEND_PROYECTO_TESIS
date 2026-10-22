from __future__ import annotations

import asyncio
import glob
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings

INTERVALO_SEGUNDOS = 3600


async def purgar_evidencia(db: AsyncIOMotorDatabase, dias: int) -> Dict[str, int]:
    """Borra las imágenes de evidencia con más de `dias` días.

    Conserva el incidente y la alerta (fecha, cámara, tipo, confianza): se
    elimina la imagen, que es el dato personal, no el registro del evento.
    Compara contra created_at, que pone siempre el backend en ISO 8601 UTC con
    el mismo formato, así que la comparación de texto equivale a la de fechas.
    """
    ahora = datetime.now(timezone.utc)
    corte = (ahora - timedelta(days=dias)).isoformat()
    filtro = {"created_at": {"$lt": corte}, "image_base64": {"$ne": None}}
    cambios = {"$set": {"image_base64": None, "evidence_purged_at": ahora.isoformat()}}

    incidentes = await db[settings.INCIDENTS_COL].update_many(filtro, cambios)
    alertas = await db[settings.ALERTS_COL].update_many(filtro, cambios)

    limite = time.time() - dias * 86400
    archivos = 0
    for ruta in glob.glob(os.path.join(settings.STATIC_DIR, "evidence_*.jpg")):
        if os.path.getmtime(ruta) < limite:
            os.remove(ruta)
            archivos += 1

    return {
        "incidentes": incidentes.modified_count,
        "alertas": alertas.modified_count,
        "archivos": archivos,
    }


async def ciclo_retencion(db: AsyncIOMotorDatabase, dias: int) -> None:
    """Purga al arrancar y luego cada hora, mientras viva la aplicación."""
    while True:
        try:
            r = await purgar_evidencia(db, dias)
            if any(r.values()):
                print(f"Retención de evidencia ({dias} días): purgados {r}", flush=True)
        except Exception as e:
            # Una purga fallida no debe tumbar el backend; se reintenta en la
            # siguiente vuelta.
            print(f"Retención de evidencia: error {e!r}", flush=True)
        await asyncio.sleep(INTERVALO_SEGUNDOS)
