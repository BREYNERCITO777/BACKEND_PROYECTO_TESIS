"""Metricas por clase con el MISMO protocolo que la Tabla 4 del manuscrito:
confidence threshold 0.001 y NMS IoU 0.5 (el que usa Ultralytics por defecto
para el computo de mAP). Corrige la corrida anterior, que uso conf=0.25 y por
eso el mAP50:95 por clase no cuadraba con el 0.545 global de la Tabla 4.
"""
import json

from ultralytics import YOLO

m = YOLO("/modelo/best.pt")
CLASES = m.names

met = m.val(data="/ext/sin_duplicados/limpio/data.yaml", split="test", conf=0.001, iou=0.5,
            plots=False, project="/ext/sin_duplicados/limpio/salida", name="val_oficial", exist_ok=True)

por_clase = {}
for i, nombre in CLASES.items():
    por_clase[nombre] = {
        "precision": float(met.box.p[i]),
        "recall": float(met.box.r[i]),
        "mAP50": float(met.box.ap50[i]),
        "mAP50_95": float(met.box.ap[i]),
    }

resumen = {
    "protocolo": "conf=0.001, iou=0.5 (igual que Tabla 4)",
    "global": {
        "precision": float(met.box.mp),
        "recall": float(met.box.mr),
        "mAP50": float(met.box.map50),
        "mAP50_95": float(met.box.map),
    },
    "por_clase": por_clase,
}
print(json.dumps(resumen, indent=2, ensure_ascii=False))
with open("/ext/sin_duplicados/limpio/salida/metricas_por_clase_oficial.json", "w") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)
