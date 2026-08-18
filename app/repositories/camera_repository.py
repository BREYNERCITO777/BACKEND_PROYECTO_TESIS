from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.crypto import cifrar, descifrar, enmascarar, huella


def _oid(id_str: str) -> ObjectId:
    return ObjectId(id_str)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara una cámara para salir por la API.

    La URL RTSP se devuelve enmascarada: lleva usuario y contraseña de la
    cámara, y no hay motivo para que esas credenciales viajen al navegador ni
    acaben en los registros del servidor. Quien necesita la URL real es el
    streaming, que la pide con rtsp_real().
    """
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    doc.pop("rtsp_hash", None)
    doc["rtsp_url"] = enmascarar(descifrar(doc.get("rtsp_url")))
    return doc


class CameraRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.col = db[settings.CAMERAS_COL]

    async def ensure_indexes(self) -> None:
        # El índice único va sobre la huella, no sobre la URL: el cifrado no es
        # determinista, asi que dos documentos con la MISMA url producirian
        # textos cifrados distintos y el indice nunca detectaria el duplicado.
        await self.col.create_index("rtsp_hash", unique=True, sparse=True)
        await self.col.create_index("created_at")

        # Retira el indice antiguo, que ahora apuntaria a texto cifrado.
        try:
            await self.col.drop_index("rtsp_url_1")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    async def list(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return [_serialize(d) for d in docs]

    async def get(self, camera_id: str) -> Optional[Dict[str, Any]]:
        try:
            d = await self.col.find_one({"_id": _oid(camera_id)})
            return _serialize(d) if d else None
        except InvalidId:
            # id mal formado
            return None

    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Busca por nombre exacto. Lo usa el agente local, que puede identificar
        la cámara con un id propio en vez del ObjectId de Mongo.
        """
        d = await self.col.find_one({"name": (name or "").strip()})
        return _serialize(d) if d else None

    async def rtsp_real(self, camera_id: str) -> Optional[str]:
        """
        Devuelve la URL RTSP descifrada, con sus credenciales.

        Es el único punto que las expone, y existe solo para que el streaming
        pueda abrir la cámara. Devuelve None si el dato no se puede descifrar,
        que es lo que ocurre si se cambió la clave.
        """
        try:
            d = await self.col.find_one({"_id": _oid(camera_id)})
        except InvalidId:
            return None
        if not d:
            return None
        return descifrar(d.get("rtsp_url"))

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    async def create(
        self,
        *,
        name: str,
        rtsp_url: str,
        enabled: bool = True,
        fps_target: int = 5,
        infer_every_n_frames: int = 5,
    ) -> Dict[str, Any]:
        # ✅ normalización básica
        name = name.strip()
        rtsp_url = rtsp_url.strip()

        doc = {
            "name": name,
            "rtsp_url": cifrar(rtsp_url),
            "rtsp_hash": huella(rtsp_url),
            "enabled": bool(enabled),
            "fps_target": int(fps_target),
            "infer_every_n_frames": int(infer_every_n_frames),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # ⚠️ si rtsp_url está duplicado, Motor lanzará DuplicateKeyError
        res = await self.col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return _serialize(doc)

    async def update(self, camera_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            # ✅ normaliza campos si vienen
            if "name" in patch and isinstance(patch["name"], str):
                patch["name"] = patch["name"].strip()

            if "rtsp_url" in patch and isinstance(patch["rtsp_url"], str):
                url = patch["rtsp_url"].strip()
                patch["rtsp_url"] = cifrar(url)
                patch["rtsp_hash"] = huella(url)

            res = await self.col.update_one({"_id": _oid(camera_id)}, {"$set": patch})
            if res.matched_count == 0:
                return None
            return await self.get(camera_id)
        except InvalidId:
            return None

    async def delete(self, camera_id: str) -> bool:
        try:
            res = await self.col.delete_one({"_id": _oid(camera_id)})
            return res.deleted_count == 1
        except InvalidId:
            return False

    async def cifrar_existentes(self) -> int:
        """
        Cifra las cámaras que quedaron guardadas en texto plano antes de que
        existiera el cifrado. Se ejecuta al arrancar y no toca las que ya
        están cifradas, asi que es seguro repetirla.
        """
        migradas = 0
        async for doc in self.col.find({}):
            url = doc.get("rtsp_url")
            if not url or url.startswith("enc:v1:"):
                continue
            await self.col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"rtsp_url": cifrar(url), "rtsp_hash": huella(url)}},
            )
            migradas += 1
        return migradas
