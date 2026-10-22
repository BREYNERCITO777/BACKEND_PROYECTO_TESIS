import cv2
import time
import os
import re
import sys
import base64
from datetime import datetime, timezone

import requests
from ultralytics import YOLO

# =========================
# CONFIGURACIÓN DESDE DOCKER
# =========================

RTSP_URL = os.getenv("RTSP_URL")
MODEL_PATH = os.getenv("MODEL_PATH", "best.pt")

BACKEND_URL = os.getenv("BACKEND_URL")
AGENT_TOKEN = os.getenv("AGENT_TOKEN")

CAMERA_ID = os.getenv("CAMERA_ID", "cam_21")
CAMERA_NAME = os.getenv("CAMERA_NAME", "Frontis MPSM - IPC")

CONFIDENCE_MIN = float(os.getenv("CONFIDENCE_MIN", "0.60"))
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "30"))

TARGET_CLASSES = ["arma_fuego", "arma_blanca"]

# Tamaño de evidencia enviada al backend
EVIDENCE_WIDTH = int(os.getenv("EVIDENCE_WIDTH", "960"))
EVIDENCE_HEIGHT = int(os.getenv("EVIDENCE_HEIGHT", "540"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "85"))

def ocultar_credenciales(url):
    """
    Reemplaza usuario:clave de una URL por ***, para no volcar la contrasena
    de la camara en los logs del contenedor.
    """
    if not url:
        return url
    return re.sub(r"://[^/@]+@", "://***:***@", url)


# Falla temprano: sin estas tres variables el agente no puede operar y es
# preferible que no arranque a que quede en un bucle de errores.
_faltantes = [
    nombre
    for nombre, valor in (
        ("RTSP_URL", RTSP_URL),
        ("BACKEND_URL", BACKEND_URL),
        ("AGENT_TOKEN", AGENT_TOKEN),
    )
    if not valor
]

if _faltantes:
    print(
        "Faltan variables de entorno obligatorias: " + ", ".join(_faltantes),
        flush=True,
    )
    print("Copia .env.example como .env y completa los valores.", flush=True)
    sys.exit(1)

print("Iniciando Sentinel AI Local Agent", flush=True)
print("RTSP:", ocultar_credenciales(RTSP_URL), flush=True)
print("Modelo:", MODEL_PATH, flush=True)
print("Backend:", BACKEND_URL, flush=True)
print("Camara:", CAMERA_ID, "-", CAMERA_NAME, flush=True)
print("Confianza minima:", CONFIDENCE_MIN, "| Cooldown:", ALERT_COOLDOWN, "s", flush=True)

print("Cargando modelo YOLO...", flush=True)
model = YOLO(MODEL_PATH)
print("Modelo YOLO cargado", flush=True)

last_alert_time = 0


def connect_camera():
    print("Conectando al RTSP...", flush=True)

    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("No se pudo conectar al RTSP", flush=True)
        return None

    print("Camara conectada correctamente", flush=True)
    return cap


def enhance_for_evidence(frame):
    """
    Mejora suave para evidencia:
    - reduce un poco contraste extremo
    - mantiene color natural
    - evita imagen demasiado chillosa
    """
    try:
        # Suavizado muy leve para ruido de CCTV
        frame = cv2.GaussianBlur(frame, (3, 3), 0)

        # Corrección suave de brillo/contraste
        alpha = 0.95  # contraste
        beta = -5     # brillo
        frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

        return frame
    except Exception:
        return frame


def draw_box(frame, label, confidence, xyxy):
    x1, y1, x2, y2 = [int(v) for v in xyxy]

    # Evitar coordenadas fuera de la imagen
    h, w = frame.shape[:2]
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w - 1))
    y2 = max(0, min(y2, h - 1))

    if label == "arma_fuego":
        color = (0, 0, 255)       # rojo
    else:
        color = (0, 165, 255)     # naranja

    # Rectángulo principal
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

    text = f"{label} {confidence:.2f}"

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    thickness = 2

    (text_width, text_height), baseline = cv2.getTextSize(
        text,
        font,
        font_scale,
        thickness
    )

    text_x = x1
    text_y = max(y1 - 10, text_height + 15)

    # Fondo del texto
    cv2.rectangle(
        frame,
        (text_x, text_y - text_height - baseline - 8),
        (text_x + text_width + 12, text_y + baseline),
        color,
        -1
    )

    # Texto blanco
    cv2.putText(
        frame,
        text,
        (text_x + 6, text_y - 5),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA
    )

    return frame


def send_alert(frame_with_boxes, label, confidence, t_captura=None, inferencia_ms=None):
    # t_captura: time.monotonic() tomado justo tras leer el frame de la
    # camara. Con el se mide cuanto tarda dibujar evidencia + codificar JPEG +
    # red, por separado de la inferencia (que ya llega medida en inferencia_ms).
    t_inicio_envio = time.monotonic()

    # Mejorar visualmente la evidencia
    frame_evidence = enhance_for_evidence(frame_with_boxes)

    # Redimensionar manteniendo tamaño usable para paper
    frame_evidence = cv2.resize(frame_evidence, (EVIDENCE_WIDTH, EVIDENCE_HEIGHT))

    ok, buffer = cv2.imencode(
        ".jpg",
        frame_evidence,
        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
    )

    if not ok:
        print("No se pudo codificar imagen JPG", flush=True)
        return

    image_base64 = base64.b64encode(buffer).decode("utf-8")

    preproc_ms = (time.monotonic() - t_inicio_envio) * 1000

    payload = {
        "camera_id": CAMERA_ID,
        "camera_name": CAMERA_NAME,
        "type": label,
        # El backend exige la confianza como probabilidad (0.0 a 1.0),
        # no como porcentaje.
        "confidence": round(float(confidence), 4),
        # Momento real de la deteccion. Sin este campo el backend usa la hora
        # en que recibe la peticion, que no es la misma si hubo demora de red.
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "docker-yolo-agent-local-municipal",
        "image_base64": image_base64,
        # Latencia end-to-end desglosada (Reviewer 1, punto 3). inferencia_ms
        # viene del bucle principal; preproc_ms cubre dibujar la evidencia,
        # redimensionar y codificar JPEG, que es lo que ocurre en esta
        # funcion antes de la llamada de red.
        "inferencia_ms": round(inferencia_ms, 1) if inferencia_ms is not None else None,
        "preproc_ms": round(preproc_ms, 1),
    }

    headers = {
        "Authorization": f"Bearer {AGENT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        t_antes_post = time.monotonic()
        response = requests.post(
            BACKEND_URL,
            json=payload,
            headers=headers,
            timeout=(10, 60),
        )
        red_ms = (time.monotonic() - t_antes_post) * 1000

        latencia_total_ms = (
            (inferencia_ms or 0) + preproc_ms + red_ms
        )
        print(
            "LATENCIA cam={} inferencia_ms={} preproc_ms={:.1f} red_ms={:.1f} "
            "total_agente_ms={:.1f}".format(
                CAMERA_ID,
                round(inferencia_ms, 1) if inferencia_ms is not None else "NA",
                preproc_ms,
                red_ms,
                latencia_total_ms,
            ),
            flush=True,
        )

        if response.status_code == 401:
            print(
                "Backend 401: AGENT_TOKEN no coincide con el del servidor",
                flush=True,
            )
            return

        if response.status_code == 422:
            print("Backend 422: payload rechazado ->", response.text[:300], flush=True)
            return

        if response.status_code not in (200, 201):
            print(
                "Error backend:", response.status_code, response.text[:300], flush=True
            )
            return

        try:
            cuerpo = response.json()
        except ValueError:
            print("ALERTA ENVIADA (respuesta no JSON)", flush=True)
            return

        # Un 200 no significa que se haya registrado: el backend descarta
        # detecciones por debajo del umbral configurado o dentro de su cooldown.
        if cuerpo.get("ignorada"):
            print(
                "Deteccion NO registrada por el backend. Motivo:",
                cuerpo.get("motivo"),
                flush=True,
            )
            return

        print("ALERTA ENVIADA - incidente", cuerpo.get("incident_id"), flush=True)

        if cuerpo.get("camera_registered") is False:
            print(
                "AVISO: la camara '{}' no esta registrada en el sistema. "
                "Registrala con el nombre exacto '{}' para vincularla.".format(
                    CAMERA_ID, CAMERA_NAME
                ),
                flush=True,
            )

    except Exception as e:
        print("Error enviando alerta:", str(e), flush=True)


cap = connect_camera()
failed_frames = 0

while True:
    if cap is None:
        time.sleep(5)
        cap = connect_camera()
        continue

    t_lectura = time.monotonic()
    ret, frame = cap.read()
    lectura_ms = (time.monotonic() - t_lectura) * 1000

    if not ret or frame is None:
        failed_frames += 1
        print(f"Error leyendo frame ({failed_frames})", flush=True)

        if failed_frames >= 5:
            print("Stream inestable. Reconectando RTSP...", flush=True)

            try:
                cap.release()
            except Exception:
                pass

            cap = None
            failed_frames = 0
            time.sleep(3)

        continue

    failed_frames = 0

    t_captura = time.monotonic()
    results = model(frame, verbose=False)
    inferencia_ms = (time.monotonic() - t_captura) * 1000

    # Latencia de inferencia de CADA frame, no solo de los que generan alerta
    # (Reviewer 1, punto 3: "per-frame inference latency"). La ruta de alerta
    # mide ademas preproc_ms y red_ms, pero esta linea es la unica forma de
    # tener P50/P95 de inferencia representativos del flujo real de video.
    # lectura_ms: espera + decodificacion del frame RTSP; es donde aparece el
    # jitter de red, que inferencia_ms no captura.
    print(
        f"LATENCIA_FRAME cam={CAMERA_ID} lectura_ms={lectura_ms:.1f} "
        f"inferencia_ms={inferencia_ms:.1f}",
        flush=True,
    )

    detections_to_send = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = model.names[cls]

            if label not in TARGET_CLASSES:
                continue

            if conf < CONFIDENCE_MIN:
                continue

            print(f"Detectado: {label} ({conf:.2f})", flush=True)

            detections_to_send.append({
                "label": label,
                "confidence": conf,
                "xyxy": box.xyxy[0],
            })

    if detections_to_send:
        current_time = time.time()

        if current_time - last_alert_time >= ALERT_COOLDOWN:
            # Escoger detección con mayor confianza
            best_detection = max(
                detections_to_send,
                key=lambda d: d["confidence"]
            )

            annotated_frame = frame.copy()

            # Dibujar todas las detecciones válidas en el frame
            for det in detections_to_send:
                annotated_frame = draw_box(
                    annotated_frame,
                    det["label"],
                    det["confidence"],
                    det["xyxy"]
                )

            print(
                f"DETECCION: {best_detection['label']} ({best_detection['confidence']:.2f})",
                flush=True
            )

            send_alert(
                annotated_frame,
                best_detection["label"],
                best_detection["confidence"],
                t_captura=t_captura,
                inferencia_ms=inferencia_ms,
            )

            last_alert_time = current_time

    time.sleep(0.2)