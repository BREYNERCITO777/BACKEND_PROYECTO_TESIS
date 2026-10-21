"""Latencia por imagen en igualdad de condiciones (Reviewer 1, punto 2:
"accuracy and inference latency on the same hardware").

Una imagen por vez, como corre el agente; mide de punta a punta
(preprocesamiento + inferencia + NMS) con cuda.synchronize, sobre las mismas
200 imagenes del test externo sin duplicados, tras 20 de calentamiento. Se
mide en GPU y en CPU porque el agente puede desplegarse en cualquiera de los
dos."""
import glob
import json
import time

import cv2
import numpy as np
import torch
import yolov5
from ultralytics import YOLO

MODELOS = {
    "yolov5s_coco": ("yolov5", "/v5s/best.pt"),
    "yolov8n_coco": ("ultralytics", "/salida/yolov8n_coco/weights/best.pt"),
    "yolov8s_coco": ("ultralytics", "/salida/yolov8s_coco/weights/best.pt"),
    "v4_produccion": ("ultralytics", "/modelo/best.pt"),
}
imagenes = [cv2.imread(r) for r in sorted(glob.glob("/ext/sin_duplicados/limpio/images/test/*.jpg"))[:220]]
CALENTAMIENTO, N = 20, 200


def cargar(tipo, pesos, dispositivo):
    if tipo == "yolov5":
        m = yolov5.load(pesos, device=dispositivo)
        m.conf, m.iou = 0.25, 0.45
        return lambda img: m(img[..., ::-1], size=640)  # AutoShape espera RGB
    m = YOLO(pesos)
    return lambda img: m.predict(img, imgsz=640, conf=0.25, device=dispositivo, verbose=False)


def medir(f, dispositivo):
    tiempos = []
    for i, img in enumerate(imagenes[: CALENTAMIENTO + N]):
        if dispositivo != "cpu":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        f(img)
        if dispositivo != "cpu":
            torch.cuda.synchronize()
        if i >= CALENTAMIENTO:
            tiempos.append((time.perf_counter() - t0) * 1000)
    t = np.array(tiempos)
    return {"P50_ms": round(float(np.percentile(t, 50)), 1),
            "P95_ms": round(float(np.percentile(t, 95)), 1),
            "media_ms": round(float(t.mean()), 1)}


resultados = {}
for nombre, (tipo, pesos) in MODELOS.items():
    resultados[nombre] = {}
    for dispositivo in ("cuda:0", "cpu"):
        resultados[nombre][dispositivo] = medir(cargar(tipo, pesos, dispositivo), dispositivo)
        print(nombre, dispositivo, resultados[nombre][dispositivo], flush=True)

resultados["_entorno"] = {"torch": torch.__version__, "gpu": torch.cuda.get_device_name(0),
                          "hilos_cpu_torch": torch.get_num_threads()}
with open("/salida/benchmark_latencia.json", "w") as f:
    json.dump(resultados, f, indent=2)
