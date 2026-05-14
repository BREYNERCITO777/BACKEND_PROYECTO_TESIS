from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception as e:
        raise ValueError("Invalid ObjectId") from e


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": str(doc["_id"]),
        "type": doc.get("type") or doc.get("weapon_type") or "ALERTA",
        "title": doc.get("title"),
        "message": doc.get("message"),
        "severity": doc.get("severity", "medium"),
        "weapon_type": doc.get("weapon_type"),
        "confidence": doc.get("confidence"),
        "evidence_url": doc.get("evidence_url"),
        "image_base64": doc.get("image_base64"),
        "evidence_type": doc.get("evidence_type"),
        "camera_id": doc.get("camera_id"),
        "camera_name": doc.get("camera_name"),
        "incident_id": doc.get("incident_id"),
        "source": doc.get("source"),
        "timestamp": doc.get("timestamp"),
        "created_at": doc.get("created_at"),
        "read": doc.get("read", False),
    }


class AlertRepository:
    def col(self, db: AsyncIOMotorDatabase):
        return db[settings.ALERTS_COL]

    async def create(
        self,
        db: AsyncIOMotorDatabase,
        *,
        title: str,
        message: str,
        severity: str = "medium",
        weapon_type: Optional[str] = None,
        confidence: Optional[float] = None,
        evidence_url: Optional[str] = None,
        camera_id: Optional[str] = None,
        read: bool = False,
        image_base64: Optional[str] = None,
        evidence_type: Optional[str] = None,
        camera_name: Optional[str] = None,
        incident_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        doc = {
            "type": weapon_type or "ALERTA",
            "title": title,
            "message": message,
            "severity": severity,
            "weapon_type": weapon_type,
            "confidence": confidence,
            "evidence_url": evidence_url,
            "image_base64": image_base64,
            "evidence_type": evidence_type,
            "camera_id": camera_id,
            "camera_name": camera_name,
            "incident_id": incident_id,
            "source": source,
            "timestamp": now,
            "created_at": now,
            "read": read,
        }

        res = await self.col(db).insert_one(doc)
        doc["_id"] = res.inserted_id

        return _serialize(doc)

    async def list(
        self,
        db: AsyncIOMotorDatabase,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        cursor = self.col(db).find({}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)

        return [_serialize(doc) for doc in docs]

    async def get(
        self,
        db: AsyncIOMotorDatabase,
        alert_id: str,
    ) -> Optional[Dict[str, Any]]:
        doc = await self.col(db).find_one({"_id": _oid(alert_id)})

        return _serialize(doc) if doc else None

    async def mark_read(
        self,
        db: AsyncIOMotorDatabase,
        alert_id: str,
        read: bool = True,
    ) -> Optional[Dict[str, Any]]:
        await self.col(db).update_one(
            {"_id": _oid(alert_id)},
            {"$set": {"read": read}},
        )

        return await self.get(db, alert_id)

    async def delete(
        self,
        db: AsyncIOMotorDatabase,
        alert_id: str,
    ) -> bool:
        res = await self.col(db).delete_one({"_id": _oid(alert_id)})

        return res.deleted_count == 1

    async def delete_all(
        self,
        db: AsyncIOMotorDatabase,
    ) -> int:
        res = await self.col(db).delete_many({})

        return int(res.deleted_count)


alert_repo = AlertRepository()
