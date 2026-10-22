"""Inferencia YOLO sobre una imagen."""

from __future__ import annotations

import time
import cv2
import numpy as np


class DetectionService:
    """Inferencia YOLO sobre imágenes sueltas."""
    def detect(self, model, image_bytes: bytes):
        """Decodifica la imagen, corre el modelo y devuelve (frame, detecciones, ms de inferencia)."""
        if model is None:
            raise RuntimeError("Modelo no cargado")

        # bytes -> OpenCV frame
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise RuntimeError("No se pudo decodificar la imagen")

        t0 = time.time()
        results = model(frame)
        infer_ms = round((time.time() - t0) * 1000, 2)

        detections = []
        r0 = results[0]
        if r0.boxes is not None:
            names = r0.names
            for b in r0.boxes:
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                x1, y1, x2, y2 = [float(x) for x in b.xyxy[0]]
                detections.append({
                    "class_id": cls_id,
                    "class_name": names.get(cls_id, str(cls_id)),
                    "confidence": round(conf, 4),
                    "box": [x1, y1, x2, y2],
                })

        return frame, detections, infer_ms