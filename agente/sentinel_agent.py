import cv2
import time
import os
import re
import sys
import json
import base64
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from ultralytics import YOLO

# =========================
# CONFIGURACIÓN DESDE DOCKER
# =========================

MODEL_PATH = os.getenv("MODEL_PATH", "best.pt")

BACKEND_URL = os.getenv("BACKEND_URL")
AGENT_TOKEN = os.getenv("AGENT_TOKEN")

CONFIDENCE_MIN = float(os.getenv("CONFIDENCE_MIN", "0.60"))
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "30"))

TARGET_CLASSES = ["arma_fuego", "arma_blanca"]

# Tamaño de evidencia enviada al backend
EVIDENCE_WIDTH = int(os.getenv("EVIDENCE_WIDTH", "960"))
EVIDENCE_HEIGHT = int(os.getenv("EVIDENCE_HEIGHT", "540"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "85"))

# Cada camara se analiza como maximo una vez por este intervalo (~5 FPS); los
# frames intermedios se descartan. Es la estrategia de frame skipping.
INTERVALO_ANALISIS = 0.2


def ocultar_credenciales(url):
    """
    Reemplaza usuario:clave de una URL por ***, para no volcar la contrasena
    de la camara en los logs del contenedor.
    """
    if not url:
        return url
    return re.sub(r"://[^/@]+@", "://***:***@", url)


def leer_camaras():
    """
    Devuelve la lista de camaras a vigilar.

    Varias camaras: CAMARAS con una lista JSON de objetos {id, nombre,
    rtsp_url}. Una sola: RTSP_URL, CAMERA_ID y CAMERA_NAME, como siempre; asi
    un .env de una camara sigue funcionando sin cambios.
    """
    texto = os.getenv("CAMARAS", "").strip()
    if texto:
        try:
            camaras = json.loads(texto)
        except ValueError as e:
            sys.exit(f"CAMARAS no es JSON valido: {e}")
        for c in camaras:
            if not all(c.get(k) for k in ("id", "nombre", "rtsp_url")):
                sys.exit("Cada camara de CAMARAS necesita id, nombre y rtsp_url")
        if len({c["id"] for c in camaras}) != len(camaras):
            sys.exit("CAMARAS tiene ids repetidos")
        return camaras

    rtsp = os.getenv("RTSP_URL")
    if not rtsp:
        return []
    return [{
        "id": os.getenv("CAMERA_ID", "cam_21"),
        "nombre": os.getenv("CAMERA_NAME", "Frontis MPSM - IPC"),
        "rtsp_url": rtsp,
    }]


CAMARAS = leer_camaras()

# Falla temprano: sin camaras, backend o token el agente no puede operar y es
# preferible que no arranque a que quede en un bucle de errores.
_faltantes = [
    nombre
    for nombre, valor in (
        ("RTSP_URL o CAMARAS", CAMARAS),
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
print("Modelo:", MODEL_PATH, flush=True)
print("Backend:", BACKEND_URL, flush=True)
for c in CAMARAS:
    print("Camara:", c["id"], "-", c["nombre"], "|", ocultar_credenciales(c["rtsp_url"]), flush=True)
print("Confianza minima:", CONFIDENCE_MIN, "| Cooldown:", ALERT_COOLDOWN, "s", flush=True)

print("Cargando modelo YOLO...", flush=True)
model = YOLO(MODEL_PATH)
print("Modelo YOLO cargado", flush=True)


class Camara(threading.Thread):
    """
    Lee una camara en su propio hilo y conserva solo el frame mas reciente.

    Leer de forma continua vacia el buffer RTSP: el bucle principal analiza
    siempre lo ultimo que vio la camara, no un frame atrasado. Un archivo de
    video (pruebas de carga) se lee a su propio FPS, para que se comporte como
    una camara y no se consuma de golpe.
    """

    def __init__(self, cid, nombre, url):
        super().__init__(daemon=True, name=f"camara-{cid}")
        self.id, self.nombre, self.url = cid, nombre, url
        self.es_archivo = "://" not in url
        self._lock = threading.Lock()
        self._frame = None
        self._lectura_ms = 0.0
        self._numero = 0

    def ultimo(self):
        """(numero, frame, lectura_ms) del frame mas reciente; numero 0 = ninguno."""
        with self._lock:
            return self._numero, self._frame, self._lectura_ms

    def _conectar(self):
        print(f"[{self.id}] Conectando...", flush=True)
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            print(f"[{self.id}] No se pudo conectar", flush=True)
            return None
        print(f"[{self.id}] Camara conectada correctamente", flush=True)
        return cap

    def run(self):
        cap, fallos = None, 0
        while True:
            if cap is None:
                cap = self._conectar()
                if cap is None:
                    time.sleep(5)
                    continue
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                pausa = 1.0 / fps if self.es_archivo else 0.0

            t = time.monotonic()
            ok, frame = cap.read()
            lectura_ms = (time.monotonic() - t) * 1000

            if not ok or frame is None:
                fallos += 1
                if fallos >= 5:
                    print(f"[{self.id}] Stream inestable. Reconectando...", flush=True)
                    cap.release()
                    cap, fallos = None, 0
                    time.sleep(3)
                continue

            fallos = 0
            with self._lock:
                self._frame, self._lectura_ms = frame, lectura_ms
                self._numero += 1
            if pausa:
                time.sleep(pausa)


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


def send_alert(camara, frame_with_boxes, label, confidence, inferencia_ms=None):
    # Corre en el pool de envios: una alerta lenta no frena a las demas camaras.
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
        "camera_id": camara.id,
        "camera_name": camara.nombre,
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
                camara.id,
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

        print(f"[{camara.id}] ALERTA ENVIADA - incidente", cuerpo.get("incident_id"), flush=True)

        if cuerpo.get("camera_registered") is False:
            print(
                "AVISO: la camara '{}' no esta registrada en el sistema. "
                "Registrala con el nombre exacto '{}' para vincularla.".format(
                    camara.id, camara.nombre
                ),
                flush=True,
            )

    except Exception as e:
        print(f"[{camara.id}] Error enviando alerta:", str(e), flush=True)


def detecciones_validas(resultado):
    salida = []
    for box in resultado.boxes:
        label = model.names[int(box.cls[0])]
        conf = float(box.conf[0])
        if label in TARGET_CLASSES and conf >= CONFIDENCE_MIN:
            salida.append({"label": label, "confidence": conf, "xyxy": box.xyxy[0]})
    return salida


camaras = [Camara(c["id"], c["nombre"], c["rtsp_url"]) for c in CAMARAS]
for cam in camaras:
    cam.start()

envios = ThreadPoolExecutor(max_workers=4, thread_name_prefix="envio")
ultimo_analizado = {cam.id: 0 for cam in camaras}
ultima_alerta = {cam.id: 0.0 for cam in camaras}

while True:
    t_ciclo = time.monotonic()

    # Un lote con el frame nuevo de cada camara que tenga uno: el modelo se
    # carga una sola vez y procesa todas las camaras juntas, en vez de un
    # proceso con su propia copia del modelo por camara.
    lote = []
    for cam in camaras:
        numero, frame, lectura_ms = cam.ultimo()
        if numero and numero != ultimo_analizado[cam.id]:
            ultimo_analizado[cam.id] = numero
            lote.append((cam, frame, lectura_ms))

    if lote:
        t_inferencia = time.monotonic()
        resultados = model([frame for _, frame, _ in lote], verbose=False)
        inferencia_ms = (time.monotonic() - t_inferencia) * 1000

        for (cam, frame, lectura_ms), resultado in zip(lote, resultados):
            # Latencia de CADA frame, no solo de los que generan alerta
            # (Reviewer 1, punto 3). inferencia_ms es la del lote completo:
            # es lo que espero este frame. lectura_ms = decodificar el frame.
            print(
                f"LATENCIA_FRAME cam={cam.id} lectura_ms={lectura_ms:.1f} "
                f"inferencia_ms={inferencia_ms:.1f} lote={len(lote)}",
                flush=True,
            )

            detecciones = detecciones_validas(resultado)
            if not detecciones:
                continue
            for d in detecciones:
                print(f"[{cam.id}] Detectado: {d['label']} ({d['confidence']:.2f})", flush=True)

            ahora = time.time()
            if ahora - ultima_alerta[cam.id] < ALERT_COOLDOWN:
                continue
            ultima_alerta[cam.id] = ahora

            mejor = max(detecciones, key=lambda d: d["confidence"])
            anotado = frame.copy()
            for d in detecciones:
                anotado = draw_box(anotado, d["label"], d["confidence"], d["xyxy"])
            print(f"[{cam.id}] DETECCION: {mejor['label']} ({mejor['confidence']:.2f})", flush=True)
            envios.submit(send_alert, cam, anotado, mejor["label"], mejor["confidence"], inferencia_ms)

    time.sleep(max(0.0, INTERVALO_ANALISIS - (time.monotonic() - t_ciclo)))