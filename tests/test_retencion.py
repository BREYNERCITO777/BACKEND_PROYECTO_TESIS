"""Retención de evidencia (punto 11 de la revisión de Frontiers).

La purga debe borrar la IMAGEN vencida y conservar el REGISTRO del incidente:
el dato personal es el fotograma, no el hecho de que hubo una detección.
"""
import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.services.retention_service import purgar_evidencia
from conftest import MONGO_URL

MARCA = "prueba-retencion"
# Base propia y desechable: la purga actúa sobre TODA la base que recibe, y
# corrida sobre la de desarrollo borraría imágenes reales de más de 30 días.
BASE_DE_PRUEBA = "sentinel_prueba_retencion"


def _hace(dias):
    return (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()


def test_purga_imagenes_vencidas_y_conserva_registros(tmp_path, monkeypatch):
    # La purga borra archivos de STATIC_DIR: en la prueba apunta a un
    # directorio temporal, nunca a la evidencia real del equipo.
    monkeypatch.setattr(settings, "STATIC_DIR", str(tmp_path))
    viejo = tmp_path / "evidence_viejo.jpg"
    nuevo = tmp_path / "evidence_nuevo.jpg"
    viejo.write_bytes(b"x")
    nuevo.write_bytes(b"x")
    hace_40_dias = time.time() - 40 * 86400
    os.utime(viejo, (hace_40_dias, hace_40_dias))

    async def correr():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[BASE_DE_PRUEBA]
        cols = [db[settings.INCIDENTS_COL], db[settings.ALERTS_COL]]
        try:
            for col in cols:
                await col.insert_many([
                    {"source": MARCA, "edad": "vieja", "created_at": _hace(40), "image_base64": "AAAA"},
                    {"source": MARCA, "edad": "reciente", "created_at": _hace(1), "image_base64": "BBBB"},
                ])

            resultado = await purgar_evidencia(db, dias=30)

            for col in cols:
                vieja = await col.find_one({"source": MARCA, "edad": "vieja"})
                reciente = await col.find_one({"source": MARCA, "edad": "reciente"})
                assert vieja is not None, "el registro vencido no debe borrarse"
                assert vieja["image_base64"] is None
                assert "evidence_purged_at" in vieja
                assert reciente["image_base64"] == "BBBB"
            return resultado
        finally:
            await client.drop_database(BASE_DE_PRUEBA)
            client.close()

    resultado = asyncio.run(correr())

    assert resultado["incidentes"] == 1
    assert resultado["alertas"] == 1
    assert not viejo.exists()
    assert nuevo.exists()
