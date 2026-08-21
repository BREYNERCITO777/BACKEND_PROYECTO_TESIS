from __future__ import annotations

import base64
import os
import uuid
from typing import Optional, Tuple

import cv2

from app.core.config import settings


def draw_boxes(frame, detections):
    for d in detections:
        x1, y1, x2, y2 = d["box"]
        p1 = (int(x1), int(y1))
        p2 = (int(x2), int(y2))

        cv2.rectangle(frame, p1, p2, (0, 0, 255), 2)
        label = f'{d["class_name"]} {int(d["confidence"]*100)}%'
        cv2.putText(frame, label, (p1[0], max(p1[1] - 8, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return frame


def save_evidence(frame, detections) -> str:
    """
    Guarda la evidencia en disco y devuelve su URL.

    ⚠️ El archivo NO sobrevive a un redespliegue: en Render, y en cualquier
    contenedor, el sistema de archivos se descarta al recrearlo. Un incidente
    guardado asi queda en la base apuntando a una imagen que ya no existe.
    Para conservarla, usa preparar_evidencia().
    """
    url, _ = preparar_evidencia(frame, detections)
    if not url:
        raise RuntimeError("No se pudo guardar la evidencia")
    return url


def preparar_evidencia(frame, detections) -> Tuple[Optional[str], Optional[str]]:
    """
    Devuelve (url_en_disco, imagen_en_base64) con las cajas ya dibujadas.

    La copia en base64 es la que se guarda dentro del propio incidente, y por
    tanto la unica que persiste: vive en MongoDB, no en el sistema de archivos
    del contenedor. Es el mismo mecanismo que ya usaba el agente local.

    La copia en disco se mantiene porque sirve las imagenes por HTTP sin
    inflar las respuestas de la API, pero es prescindible.
    """
    frame2 = draw_boxes(frame.copy(), detections)

    ok, buffer = cv2.imencode(".jpg", frame2, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return None, None

    datos = buffer.tobytes()

    # Mongo rechaza documentos de mas de 16 MB; una captura JPEG ronda los
    # 100 KB, pero se comprueba por si llega un fotograma muy grande.
    limite = int(settings.AGENT_MAX_EVIDENCE_MB * 1024 * 1024)
    en_base64 = base64.b64encode(datos).decode("ascii") if len(datos) <= limite else None

    url = None
    try:
        os.makedirs(settings.STATIC_DIR, exist_ok=True)
        nombre = f"evidence_{uuid.uuid4().hex}.jpg"
        with open(os.path.join(settings.STATIC_DIR, nombre), "wb") as f:
            f.write(datos)
        url = f"/static/{nombre}"
    except OSError:
        # Si el disco falla, la evidencia sigue viajando en base64.
        url = None

    return url, en_base64