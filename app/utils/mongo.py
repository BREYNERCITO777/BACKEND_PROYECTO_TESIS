"""Conversiones entre ObjectId de Mongo y texto."""

# app/utils/mongo.py
from __future__ import annotations

from bson import ObjectId


def to_object_id(value: str) -> ObjectId:
    """Convierte un id de texto en ObjectId."""
    return ObjectId(value)


def oid_str(oid) -> str:
    """Convierte un ObjectId en texto."""
    return str(oid)


def normalize_mongo_id(doc: dict) -> dict:
    """
    Convierte _id:ObjectId -> _id:str para que sea JSON-friendly.
    """
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc
