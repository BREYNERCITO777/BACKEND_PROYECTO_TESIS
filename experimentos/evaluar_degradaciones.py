import json
from ultralytics import YOLO

MODELO = "/modelo/best.pt"
m = YOLO(MODELO)

resultados = {}
for nombre in ["blur", "compresion", "oclusion"]:
    data_yaml = f"/data/degradaciones/{nombre}/data.yaml"
    met = m.val(data=data_yaml, split="test", conf=0.25, iou=0.5, plots=False, verbose=False)
    resultados[nombre] = {
        "precision": float(met.box.mp),
        "recall": float(met.box.mr),
        "mAP50": float(met.box.map50),
        "mAP50_95": float(met.box.map),
    }
    print(nombre, resultados[nombre])

with open("/data/degradaciones/resultados.json", "w") as f:
    json.dump(resultados, f, indent=2)
