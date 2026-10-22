"""Evalua todos los modelos en los conjuntos de angulo de camara
(generar_angulos.py) con el mismo protocolo que evaluar_todo.py y
evaluar_yolov5.py (conf=0.001, IoU de NMS 0.5). YOLOv5s va aparte, en
evaluar_angulos_yolov5.py, porque usa el paquete yolov5."""
import json

MODELOS = {
    "v3_anterior": "/pesos/v3.pt",
    "yolov8n_coco": "/salida_noche/yolov8n_coco/weights/best.pt",
    "yolov8s_coco": "/salida_noche/yolov8s_coco/weights/best.pt",
    "v4_produccion": "/pesos/v4.pt",
    "v5_aumentado": "/salida_noche/modelo_v5/weights/best.pt",
}
CONJUNTOS = {c: f"/ext/sin_duplicados/{c}/data.yaml" for c in ("limpio", "elevada", "lateral")}


def resumen(mp, mr, m50, m5095):
    return {"precision": round(float(mp), 4), "recall": round(float(mr), 4),
            "mAP50": round(float(m50), 4), "mAP50_95": round(float(m5095), 4)}


res = {}
from ultralytics import YOLO  # noqa: E402

for nombre, pesos in MODELOS.items():
    m = YOLO(pesos)
    res[nombre] = {}
    for c, yaml in CONJUNTOS.items():
        b = m.val(data=yaml, split="test", conf=0.001, iou=0.5, plots=False, verbose=False,
                  batch=8, workers=2).box
        res[nombre][c] = resumen(b.mp, b.mr, b.map50, b.map)
        print(nombre, c, res[nombre][c], flush=True)

json.dump(res, open("/salida/evaluacion_angulos.json", "w"), indent=2)
print("Guardado /salida/evaluacion_angulos.json")
