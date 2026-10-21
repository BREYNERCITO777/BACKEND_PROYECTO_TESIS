"""YOLOv5s con el mismo protocolo que evaluar_todo.py (conf=0.001, IoU de NMS
0.5, mismos conjuntos sin duplicados) para que la comparacion de arquitecturas
sea en igualdad de condiciones. Se corre aparte porque usa el paquete yolov5.
Ver evaluar_todo.py sobre los conjuntos."""
import json

from yolov5 import val

PESOS = "/v5s/best.pt"
CONJUNTOS = {"test_completo_con_duplicados": "/ext/eval_dataset/data.yaml"}
for c in ("limpio", "compresion", "blur", "oclusion", "desenfoque", "baja_luz"):
    CONJUNTOS[c] = f"/ext/sin_duplicados/{c}/data.yaml"

for nombre_c, yaml in list(CONJUNTOS.items()):
    tmp = f"/tmp/{nombre_c}.yaml"
    with open(yaml) as f:
        texto = f.read().replace("path: /data/", "path: /ext/")
    with open(tmp, "w") as f:
        f.write(texto)
    CONJUNTOS[nombre_c] = tmp

resultados = {}
for nombre_c, yaml in CONJUNTOS.items():
    (mp, mr, map50, map5095, *_), *_ = val.run(
        data=yaml, weights=PESOS, task="test", imgsz=640, batch_size=8,
        conf_thres=0.001, iou_thres=0.5, workers=2, plots=False,
        project="/tmp/v5val", name=nombre_c, exist_ok=True,
    )
    resultados[nombre_c] = {
        "precision": round(float(mp), 4),
        "recall": round(float(mr), 4),
        "mAP50": round(float(map50), 4),
        "mAP50_95": round(float(map5095), 4),
    }
    print("yolov5s_coco", nombre_c, resultados[nombre_c], flush=True)

with open("/salida/evaluacion_yolov5s.json", "w") as f:
    json.dump({"yolov5s_coco": resultados}, f, indent=2)
