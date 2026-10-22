"""YOLOv5s en los conjuntos de angulo de camara, con el mismo protocolo que
evaluar_angulos.py. Requiere el paquete yolov5 (ver entrenar_yolov5.sh)."""
import json

from yolov5 import val

res = {}
for c in ("limpio", "elevada", "lateral"):
    (mp, mr, m50, m5095, *_), *_ = val.run(
        data=f"/ext/sin_duplicados/{c}/data.yaml", weights="/pesos/v5s.pt", task="test", imgsz=640,
        batch_size=8, conf_thres=0.001, iou_thres=0.5, workers=2, plots=False,
        project="/tmp/v5val", name=c, exist_ok=True)
    res[c] = {"precision": round(float(mp), 4), "recall": round(float(mr), 4),
              "mAP50": round(float(m50), 4), "mAP50_95": round(float(m5095), 4)}
    print("yolov5s_coco", c, res[c], flush=True)

json.dump({"yolov5s_coco": res}, open("/salida/evaluacion_angulos_yolov5s.json", "w"), indent=2)
