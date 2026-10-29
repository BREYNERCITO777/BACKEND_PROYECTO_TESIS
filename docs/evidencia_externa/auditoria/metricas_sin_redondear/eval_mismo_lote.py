"""Repite la evaluacion por clase de v5 con los parametros EXACTOS de la
evaluacion original de la Tabla 4 (cola_noche/evaluar_todo.py: conf=0.001,
iou=0.5, batch=8, workers=2) y con el batch por defecto (16), para saber si la
diferencia 0.863/0.861 en precision viene del tamano de lote."""
import json

from ultralytics import YOLO

m = YOLO("/modelo/best.pt")
yaml_src = "/ext/sin_duplicados/limpio/data.yaml"
with open(yaml_src) as f:
    texto = f.read().replace("path: /data/", "path: /ext/")
with open("/tmp/limpio.yaml", "w") as f:
    f.write(texto)

salida = {}
for batch in (8, 16):
    met = m.val(data="/tmp/limpio.yaml", split="test", conf=0.001, iou=0.5,
                plots=False, verbose=False, batch=batch, workers=2)
    salida[f"batch_{batch}"] = {
        "global": {"precision": float(met.box.mp), "recall": float(met.box.mr),
                   "mAP50": float(met.box.map50), "mAP50_95": float(met.box.map)},
        "por_clase": {m.names[i]: {"precision": float(met.box.p[i]), "recall": float(met.box.r[i]),
                                   "mAP50": float(met.box.ap50[i]), "mAP50_95": float(met.box.ap[i])}
                      for i in m.names},
    }
print(json.dumps(salida, indent=2))
with open("/ext/metricas_mismo_lote.json", "w") as f:
    json.dump(salida, f, indent=2)
