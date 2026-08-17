from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings


def _oid(id_: str) -> ObjectId:
    return ObjectId(id_)


def _sanitize_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza un documento de usuario para exponerlo hacia afuera:
    _id como string, sin password_hash y con estado entero.
    """
    doc["_id"] = str(doc["_id"])
    doc.pop("password_hash", None)
    if "estado" in doc:
        try:
            doc["estado"] = int(doc["estado"])
        except (TypeError, ValueError):
            doc["estado"] = 1
    return doc


class UserRepository:
    """
    Repositorio de usuarios con la base inyectada.

    Es el unico lugar que habla con la coleccion de usuarios: los routers no
    deben acceder a db[USERS_COL] directamente.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.col = db[settings.USERS_COL]

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Devuelve el documento CRUDO, con password_hash incluido.
        Lo necesita el login para verificar la contrasena.
        """
        return await self.col.find_one({"email": (email or "").strip().lower()})

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = await self.col.find_one({"_id": _oid(user_id)})
        except (InvalidId, TypeError):
            return None
        return _sanitize_user(doc) if doc else None

    async def get_raw_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Igual que get_by_id pero sin sanitizar. Uso interno."""
        try:
            return await self.col.find_one({"_id": _oid(user_id)})
        except (InvalidId, TypeError):
            return None

    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.col.find({}, {"password_hash": 0}).sort("email", 1).limit(limit)
        docs = await cursor.to_list(length=limit)
        for d in docs:
            d["_id"] = str(d["_id"])
            if "estado" in d:
                try:
                    d["estado"] = int(d["estado"])
                except (TypeError, ValueError):
                    d["estado"] = 1
        return docs

    async def email_exists(self, email: str, excluir_id: Optional[str] = None) -> bool:
        """
        Comprueba si el email ya esta tomado. Con excluir_id se ignora al
        propio usuario, para permitir que se reenvie su email sin cambios.
        """
        doc = await self.col.find_one({"email": (email or "").strip().lower()})
        if not doc:
            return False
        if excluir_id and str(doc.get("_id")) == excluir_id:
            return False
        return True

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: str,
        name: str = "",
        estado: int = 1,
    ) -> Dict[str, Any]:
        doc = {
            "email": (email or "").strip().lower(),
            "password_hash": password_hash,
            "role": role,
            "name": (name or "").strip(),
            "estado": int(estado),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = await self.col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return _sanitize_user(doc)

    async def update(self, user_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Aplica un parche parcial. Devuelve el usuario actualizado, o None si
        el id no existe o esta mal formado.
        """
        if not patch:
            return await self.get_by_id(user_id)

        try:
            oid = _oid(user_id)
        except (InvalidId, TypeError):
            return None

        patch = dict(patch)
        if "email" in patch and isinstance(patch["email"], str):
            patch["email"] = patch["email"].strip().lower()
        if "name" in patch and isinstance(patch["name"], str):
            patch["name"] = patch["name"].strip()
        if "estado" in patch:
            patch["estado"] = int(patch["estado"])

        res = await self.col.update_one({"_id": oid}, {"$set": patch})
        if res.matched_count == 0:
            return None
        return await self.get_by_id(user_id)

    async def delete(self, user_id: str) -> bool:
        try:
            res = await self.col.delete_one({"_id": _oid(user_id)})
        except (InvalidId, TypeError):
            return False
        return res.deleted_count == 1
