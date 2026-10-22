"""Gestión de cámaras y de su procesamiento en vivo."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.core.database import get_db
from app.core.security import require_roles
from app.repositories.camera_repository import CameraRepository
from app.services.camera_manager import camera_manager

router = APIRouter(prefix="/cameras", tags=["Cameras"])


# ---------- SCHEMAS ----------

class CameraCreate(BaseModel):
    name: str = Field(..., min_length=2)
    rtsp_url: str = Field(..., min_length=5)
    enabled: bool = True
    fps_target: int = Field(default=5, ge=1, le=120)
    infer_every_n_frames: int = Field(default=5, ge=1, le=120)


class CameraPatch(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    enabled: Optional[bool] = None
    fps_target: Optional[int] = Field(default=None, ge=1, le=120)
    infer_every_n_frames: Optional[int] = Field(default=None, ge=1, le=120)


# ---------- ENDPOINTS ----------

# ✅ LISTAR: admin/operator (solo ver)
@router.get("")
async def list_cameras(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin", "operator")),
):
    """Cámaras registradas, con la URL RTSP enmascarada."""
    return await CameraRepository(db).list()


# ✅ CREAR: SOLO admin
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Registra una cámara; 409 si su URL RTSP ya existe."""
    try:
        return await CameraRepository(db).create(**payload.model_dump())
    except DuplicateKeyError as e:
        dup_rtsp = None
        try:
            details = getattr(e, "details", None) or {}
            key_value = details.get("keyValue") or {}
            dup_rtsp = key_value.get("rtsp_url")
        except Exception:
            pass

        msg = "Ya existe una cámara con ese rtsp_url."
        if dup_rtsp:
            msg = f"Ya existe una cámara con rtsp_url='{dup_rtsp}'."

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)


# ✅ UPDATE: SOLO admin
@router.patch("/{camera_id}")
async def update_camera(
    camera_id: str,
    payload: CameraPatch,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Actualiza los datos de una cámara."""
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    doc = await CameraRepository(db).update(camera_id, patch)
    if not doc:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return doc


# ✅ DELETE: SOLO admin
@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Borra una cámara."""
    ok = await CameraRepository(db).delete(camera_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    # limpiar semáforo en memoria
    active_streams = getattr(request.app.state, "active_streams", {})
    active_streams.pop(camera_id, None)

    # detener stream si estaba corriendo
    try:
        camera_manager.stop(camera_id)
    except Exception:
        pass

    return {"deleted": True, "camera_id": camera_id}


# ✅ CAMBIAR STATUS: SOLO admin (porque modifica)
# Nota: lo dejo con query param ?status_=RUNNING|STOPPED para que sea claro en Swagger.
@router.patch("/{camera_id}/status")
async def update_camera_status(
    camera_id: str,
    status_: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Cambia el estado de la cámara a RUNNING o STOPPED."""
    if status_ not in ["RUNNING", "STOPPED"]:
        raise HTTPException(status_code=400, detail="Estado inválido (RUNNING|STOPPED)")

    # 1) Actualiza en Mongo
    doc = await CameraRepository(db).update(camera_id, {"status": status_})
    if not doc:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    # 2) Semáforo en memoria + detener si es STOPPED
    active_streams = getattr(request.app.state, "active_streams", {})
    if status_ == "RUNNING":
        active_streams[camera_id] = True
    else:
        active_streams[camera_id] = False
        try:
            camera_manager.stop(camera_id)
        except Exception:
            pass

    return {"camera_id": camera_id, "status": status_}


# ✅ START: SOLO admin
@router.post("/{camera_id}/start")
async def start_camera(
    camera_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Arranca el procesamiento en vivo de una cámara en el backend."""
    cam = await CameraRepository(db).get(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    await CameraRepository(db).update(camera_id, {"status": "RUNNING"})

    active_streams = getattr(request.app.state, "active_streams", {})
    active_streams[camera_id] = True

    return {"camera_id": camera_id, "running": True}


# ✅ STOP: SOLO admin
@router.post("/{camera_id}/stop")
async def stop_camera(
    camera_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Detiene el procesamiento en vivo de una cámara."""
    await CameraRepository(db).update(camera_id, {"status": "STOPPED"})

    active_streams = getattr(request.app.state, "active_streams", {})
    active_streams[camera_id] = False

    try:
        camera_manager.stop(camera_id)
    except Exception:
        pass

    return {"camera_id": camera_id, "running": False}


# ✅ VER ESTADO DEL MANAGER (solo ver): admin/operator
@router.get("/status")
async def cameras_status(
    _user=Depends(require_roles("admin", "operator")),
):
    """Estado de los procesamientos en vivo activos."""
    return camera_manager.status()