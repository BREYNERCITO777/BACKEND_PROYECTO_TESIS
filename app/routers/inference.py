from __future__ import annotations

import os
import time
import asyncio
import cv2
from collections import deque
from typing import Optional, Any, Deque, Dict, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_token

from app.repositories.incident_repository import IncidentRepository
from app.repositories.alert_repository import alert_repo
from app.repositories.camera_repository import CameraRepository
from app.repositories.settings_repository import settings_repo
from app.repositories.user_repository import UserRepository
from app.services.detection_service import DetectionService
from app.services.evidence_service import preparar_evidencia

# Opciones de FFmpeg para RTSP. Deben definirse antes de crear cualquier
# VideoCapture, y son la diferencia entre un backend estable y uno que se cuelga:
#   - rtsp_transport;tcp  -> por defecto FFmpeg negocia UDP, que con cámaras IP
#     pierde paquetes y deja lecturas a medias.
#   - timeout / stimeout  -> sin un límite, abrir o leer de una cámara que deja
#     de responder espera indefinidamente dentro de OpenCV, que no libera el GIL
#     mientras tanto, y el proceso entero deja de atender peticiones.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|timeout;5000000|stimeout;5000000",
)

router = APIRouter(prefix="/inference", tags=["Inference"])
service = DetectionService()

# ==========================================
# CONFIGURACIÓN: Nivel de Confianza Mínimo
# ==========================================
# No se escribe aquí: sale de /settings, el mismo valor que aplica el endpoint
# del agente, para que el panel sea la única fuente de la sensibilidad.
# Un stream en curso lo relee cada tantos segundos.
REFRESCO_UMBRAL_SEG = 30.0


async def _umbral_actual(db: AsyncIOMotorDatabase) -> float:
    config = await settings_repo.get_or_create(db)
    return float(config.get("confidence_threshold", settings.CONF_TH))


async def _inferir_cada_n(db: AsyncIOMotorDatabase, camera_id: str) -> int:
    """Cada cuántos fotogramas se ejecuta el modelo en esta cámara.

    Manda el valor de la cámara; si no lo tiene, el general de /settings. Se lee
    una vez al abrir la transmisión: cambiarlo afecta a la siguiente, no a la
    que ya está en curso.
    """
    try:
        camara = await CameraRepository(db).get(camera_id)
        if camara and camara.get("infer_every_n_frames"):
            return max(1, int(camara["infer_every_n_frames"]))
    except Exception:
        pass

    try:
        config = await settings_repo.get_or_create(db)
        return max(1, int(config.get("infer_every_n_frames", 1)))
    except Exception:
        return 1


def _severity_from_conf(conf: float) -> str:
    if conf >= 0.90:
        return "critical"
    if conf >= 0.80:
        return "high"
    if conf >= 0.70:
        return "medium"
    return "low"


def _alert_title(_weapon_type: str, severity: str) -> str:
    if severity == "critical":
        return "Detección Crítica"
    if severity == "high":
        return "Detección Alta"
    return "Detección"


def _alert_message(weapon_type: str, confidence: float, camera_id: str | None) -> str:
    cam = camera_id or "—"
    return f'Se detectó "{weapon_type}" con {(confidence*100):.0f}% de confianza. Cámara: {cam}'


# ==========================================================
# ✅ Auth helper: acepta Bearer header o ?token=...
# ==========================================================
def _extract_bearer(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    auth = auth.strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


async def _get_user_from_token(token: str, db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin 'sub'")

    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Token sub inválido")

    # get_by_id ya devuelve _id como string y sin password_hash.
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    return user


async def require_roles_stream(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """
    ✅ Para streaming / detectar: permite autenticar por:
    - Header Authorization: Bearer <jwt>
    - Query param ?token=<jwt> (para <img src="...">)
    """
    jwt_token = _extract_bearer(request) or token
    if not jwt_token:
        raise HTTPException(status_code=401, detail="No autorizado")

    user = await _get_user_from_token(jwt_token, db)
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="No tienes permisos")

    return user


# ==========================================
# ENDPOINT: Detección por foto estática
# ==========================================
@router.post("/detectar")
async def detectar(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_roles_stream),
):
    t0 = time.time()
    try:
        model = getattr(request.app.state, "yolo_model", None)
        if model is None:
            raise RuntimeError("Modelo no cargado en el servidor")

        image_bytes = await file.read()
        frame, raw_detections, infer_ms = service.detect(model, image_bytes)

        umbral = await _umbral_actual(db)
        detections = [d for d in raw_detections if d.get("confidence", 0.0) >= umbral]

        if not detections:
            return {
                "detections": [],
                "latency_infer_ms": infer_ms,
                "latency_e2e_ms": round((time.time() - t0) * 1000, 2),
                "evidence_url": None,
                "umbral_aplicado": umbral,
                "detecciones_descartadas": len(raw_detections),
            }

        # Se guardan las dos copias: el archivo sirve las imagenes por HTTP,
        # pero desaparece en cada redespliegue del contenedor. La copia en
        # base64 viaja dentro del incidente y vive en Mongo, que es la unica
        # que persiste. Antes solo se guardaba el archivo, y por eso quedaban
        # incidentes apuntando a evidencias inexistentes.
        evidence_url, evidence_b64 = preparar_evidencia(frame, detections)

        top = max(detections, key=lambda d: d["confidence"])
        weapon_type = top["class_name"]
        confidence = float(top["confidence"])
        severity = _severity_from_conf(confidence)

        incident_repo = IncidentRepository(db)
        incident = await incident_repo.create(
            weapon_type=weapon_type,
            confidence=confidence,
            evidence_url=evidence_url,
            camera_id=None,
            image_base64=evidence_b64,
            evidence_type="base64" if evidence_b64 else None,
        )

        await alert_repo.create(
            db,
            title=_alert_title(weapon_type, severity),
            message=_alert_message(weapon_type, confidence, None),
            severity=severity,
            weapon_type=weapon_type,
            confidence=confidence,
            evidence_url=evidence_url,
            camera_id=None,
            read=False,
            image_base64=evidence_b64,
            evidence_type="base64" if evidence_b64 else None,
            # Sin esto la alerta quedaba huerfana: no habia forma de saber a
            # que incidente correspondia. El endpoint del agente si lo enlazaba.
            incident_id=str(incident["_id"]),
        )

        return {
            "detections": detections,
            "latency_infer_ms": infer_ms,
            "latency_e2e_ms": round((time.time() - t0) * 1000, 2),
            "evidence_url": evidence_url,
            "incident_id": str(incident["_id"]),
            "umbral_aplicado": umbral,
            "detecciones_descartadas": len(raw_detections) - len(detections),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
# ✅ Resolver fuente real: camera_id -> rtsp_url en Mongo
# ==========================================================
async def _resolve_camera_source(camera_id: str, db: AsyncIOMotorDatabase) -> int | str:
    # ⚠️ En servidores (Render) no existe webcam "0"
    # Activa ALLOW_WEBCAM=1 solo en local si deseas usar cámara laptop.
    allow_webcam = os.getenv("ALLOW_WEBCAM", "0") == "1"

    if camera_id == "0":
        if not allow_webcam:
            raise HTTPException(
                status_code=400,
                detail='camera_id="0" solo permitido en local (ALLOW_WEBCAM=1). En servidor usa RTSP/IP cam.',
            )
        return 0

    try:
        ObjectId(camera_id)
    except Exception:
        raise HTTPException(status_code=400, detail="camera_id inválido")

    repo = CameraRepository(db)

    if not await repo.get(camera_id):
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    # La URL se guarda cifrada; rtsp_real() es el único punto que la descifra.
    rtsp = await repo.rtsp_real(camera_id)
    if not rtsp:
        raise HTTPException(
            status_code=400,
            detail="La cámara no tiene una URL RTSP utilizable. Si cambió "
                   "RTSP_SECRET_KEY, vuelve a guardar la URL de la cámara.",
        )

    if isinstance(rtsp, str) and rtsp.isdigit():
        return int(rtsp)

    return str(rtsp)


def _encode_mjpeg_frame(jpg_bytes: bytes) -> bytes:
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpg_bytes)).encode() + b"\r\n\r\n"
        + jpg_bytes
        + b"\r\n"
    )


# ==========================================
# Generador MJPEG estable (corta al cerrar modal)
# ==========================================
async def generar_frames(
    request: Request,
    camera_id: str,
    camera_source: int | str,
    model,
    db: AsyncIOMotorDatabase,
):
    cap = cv2.VideoCapture(camera_source)

    # reduce lag RTSP (si aplica)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    last_alert_time = 0.0
    COOLDOWN_SECONDS = 5.0

    # Confirmación temporal: no se registra un incidente por una sola
    # inferencia, sino cuando la misma clase aparece en al menos
    # CONFIRMAR_DE de las últimas CONFIRMAR_EN.
    #
    # Un arma real permanece en escena durante segundos, así que sale en varias
    # inferencias seguidas. Un pliegue de tela, un reflejo o un objeto a
    # contraluz aparece en una y desaparece en la siguiente. Filtrar por
    # persistencia elimina ese ruido sin subir el umbral, que es lo que haría
    # perder detecciones legítimas de confianza media.
    #
    # Con la cámara tapada, el sistema llegó a registrar 908 incidentes en un
    # día por este camino, todos falsos y todos de una sola inferencia.
    CONFIRMAR_DE = int(os.getenv("STREAM_CONFIRMAR_DE", "3"))
    CONFIRMAR_EN = int(os.getenv("STREAM_CONFIRMAR_EN", "5"))
    CONFIRMAR_DE = max(1, min(CONFIRMAR_DE, CONFIRMAR_EN))
    historial: Deque[Optional[str]] = deque(maxlen=CONFIRMAR_EN)

    # Umbral vigente, releído periódicamente para que un cambio en el panel
    # afecte a una transmisión en curso sin tener que reiniciarla.
    umbral = await _umbral_actual(db)
    ultimo_refresco = time.time()

    # FPS stream
    fps_target = float(os.getenv("STREAM_FPS", "12"))
    fps_target = max(2.0, min(30.0, fps_target))
    frame_interval = 1.0 / fps_target
    next_frame_time = time.time()

    # Cada cuantos fotogramas se ejecuta el modelo.
    #
    # El campo existia en la camara, en la API y en el panel, pero solo lo leia
    # el modulo de simulacion: el video real inferia en TODOS los fotogramas.
    # El operador podia cambiarlo y no pasaba nada.
    #
    # Separar las dos frecuencias importa porque el anti-avalancha ya limita a
    # un incidente cada COOLDOWN_SECONDS: a 12 fps se ejecutaban 60 inferencias
    # por cada ventana de 5 s de las que, como mucho, una llegaba a incidente.
    # Las otras 59 se descartaban por diseno. Ahora el operador ve video fluido
    # y la GPU trabaja solo lo necesario.
    inferir_cada = await _inferir_cada_n(db, camera_id)
    n_frame = 0
    # Las cajas del ultimo analisis se siguen dibujando en los fotogramas
    # intermedios; si no, el recuadro parpadearia.
    detections: List[Dict[str, Any]] = []

    active_streams = getattr(request.app.state, "active_streams", {})
    active_streams[camera_id] = True

    try:
        while True:
            if await request.is_disconnected():
                break

            if not active_streams.get(camera_id, False):
                break

            # control fps real
            now = time.time()
            sleep_for = next_frame_time - now
            if sleep_for > 0:
                await asyncio.sleep(min(sleep_for, 0.25))
            next_frame_time = max(next_frame_time + frame_interval, time.time())

            # OpenCV bloquea -> thread
            success, frame = await asyncio.to_thread(cap.read)
            if not success or frame is None:
                await asyncio.sleep(0.2)
                continue

            ret, buffer = await asyncio.to_thread(cv2.imencode, ".jpg", frame)
            if not ret:
                continue
            image_bytes = buffer.tobytes()

            if time.time() - ultimo_refresco > REFRESCO_UMBRAL_SEG:
                umbral = await _umbral_actual(db)
                ultimo_refresco = time.time()

            # infer -> thread, solo en uno de cada N fotogramas
            n_frame += 1
            if n_frame % inferir_cada == 0:
                _, raw_detections, _infer_ms = await asyncio.to_thread(
                    service.detect, model, image_bytes
                )
                detections = [
                    d for d in raw_detections if d.get("confidence", 0.0) >= umbral
                ]

                # El historial se alimenta solo cuando el modelo ha corrido de
                # verdad: si contara tambien los fotogramas intermedios, la
                # ventana medirla tiempo en vez de inferencias.
                if detections:
                    mejor = max(detections, key=lambda d: d["confidence"])
                    historial.append(mejor["class_name"])
                else:
                    historial.append(None)

            frame_draw = frame.copy()

            if detections:
                for det in detections:
                    box = det.get("box", [])
                    if len(box) == 4:
                        x1, y1, x2, y2 = map(int, box)
                        cv2.rectangle(frame_draw, (x1, y1), (x2, y2), (0, 0, 255), 2)

                        etiqueta = f"{det['class_name']} {(det['confidence']*100):.0f}%"
                        (tw, th), baseline = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                        y_text = max(y1 - 10, th + 10)

                        cv2.rectangle(
                            frame_draw,
                            (x1, y_text - th - 8),
                            (x1 + tw + 8, y_text + baseline),
                            (0, 0, 0),
                            -1,
                        )
                        cv2.putText(
                            frame_draw,
                            etiqueta,
                            (x1 + 4, y_text - 4),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 0, 255),
                            2,
                            cv2.LINE_AA,
                        )

                current_time = time.time()
                top = max(detections, key=lambda d: d["confidence"])

                # Solo se registra si la misma clase persiste en la ventana.
                # Se dibuja igualmente en pantalla: el operador ve lo que el
                # modelo cree ver, aunque no llegue a convertirse en incidente.
                confirmada = historial.count(top["class_name"]) >= CONFIRMAR_DE

                if confirmada and (current_time - last_alert_time) > COOLDOWN_SECONDS:
                    weapon_type = top["class_name"]
                    confidence = float(top["confidence"])
                    severity = _severity_from_conf(confidence)

                    # Igual que en la deteccion por foto: el archivo se pierde
                    # al redesplegar, la copia en base64 es la que persiste.
                    evidence_url, evidence_b64 = await asyncio.to_thread(
                        preparar_evidencia, frame_draw, detections
                    )

                    incident_repo = IncidentRepository(db)
                    incidente = await incident_repo.create(
                        weapon_type=weapon_type,
                        confidence=confidence,
                        evidence_url=evidence_url,
                        camera_id=camera_id,
                        image_base64=evidence_b64,
                        evidence_type="base64" if evidence_b64 else None,
                    )

                    await alert_repo.create(
                        db,
                        title=_alert_title(weapon_type, severity),
                        message=_alert_message(weapon_type, confidence, camera_id),
                        severity=severity,
                        weapon_type=weapon_type,
                        confidence=confidence,
                        evidence_url=evidence_url,
                        camera_id=camera_id,
                        read=False,
                        image_base64=evidence_b64,
                        evidence_type="base64" if evidence_b64 else None,
                        incident_id=incidente["_id"],
                    )

                    last_alert_time = current_time

            ret2, buffer2 = await asyncio.to_thread(cv2.imencode, ".jpg", frame_draw)
            if not ret2:
                continue

            yield _encode_mjpeg_frame(buffer2.tobytes())

    finally:
        try:
            cap.release()
        except Exception:
            pass
        active_streams[camera_id] = False


@router.get("/stream/{camera_id}")
async def video_stream(
    camera_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_roles_stream),
):
    model = getattr(request.app.state, "yolo_model", None)
    if model is None:
        raise HTTPException(status_code=500, detail="Modelo YOLO no cargado")

    camera_source = await _resolve_camera_source(camera_id, db)

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return StreamingResponse(
        generar_frames(request, camera_id, camera_source, model, db),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers=headers,
    )