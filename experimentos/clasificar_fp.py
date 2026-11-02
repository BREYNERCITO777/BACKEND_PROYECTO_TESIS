"""Clasifica cada falso positivo de v5 a conf 0.25 en el test depurado (1,054):
- desplazada: solapa un arma anotada de la misma clase con IoU entre 0.1 y 0.5
- otra clase: solapa (IoU >= 0.5) un arma anotada de la otra clase
- sin arma cerca: IoU < 0.1 con toda arma anotada
Tambien guarda la matriz de confusion cruda de Ultralytics (misma corrida que la Figura 8)."""
import csv, glob, json, os
import numpy as np
from ultralytics import YOLO

m = YOLO("/modelo/best.pt")
IMG = "/ext/sin_duplicados/limpio/images/test"
LAB = "/ext/sin_duplicados/limpio/labels/test"

def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1]); x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i + 1e-9)

def analizar(umbral):
  filas, tp, fn = [], 0, 0
  imgs = sorted(glob.glob(IMG + "/*"))
  for k in range(0, len(imgs), 16):
      for r in m(imgs[k:k+16], conf=umbral, iou=0.5, verbose=False):
          h, w = r.orig_shape
          gts = []
          lab = os.path.join(LAB, os.path.splitext(os.path.basename(r.path))[0] + ".txt")
          if os.path.exists(lab):
              for l in open(lab):
                  c, x, y, bw, bh = map(float, l.split())
                  gts.append((int(c), [(x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h]))
          preds = sorted(zip(r.boxes.conf.tolist(), r.boxes.cls.int().tolist(), r.boxes.xyxy.tolist()), reverse=True)
          usado = set()
          for conf, c, b in preds:
              cand = [(iou(b, g), j) for j, (gc, g) in enumerate(gts) if gc == c and j not in usado]
              mejor = max(cand, default=(0, -1))
              if mejor[0] >= 0.5:
                  usado.add(mejor[1]); tp += 1; continue
              misma = max([iou(b, g) for gc, g in gts if gc == c], default=0)
              otra = max([iou(b, g) for gc, g in gts if gc != c], default=0)
              tipo = ("desplazada" if 0.1 <= misma < 0.5 else "otra_clase" if otra >= 0.5
                      else "duplicada" if misma >= 0.5 else "sin_arma_cerca")
              filas.append([os.path.basename(r.path), c, round(conf, 3), round(misma, 3), round(otra, 3), tipo])
          fn += len(gts) - len(usado)
  return filas, tp, fn

os.makedirs("/ext/fp_analisis", exist_ok=True)
from collections import Counter
res = {}
for umbral in (0.25, 0.65):
    filas, tp, fn = analizar(umbral)
    with open(f"/ext/fp_analisis/falsos_positivos_{umbral}.csv", "w", newline="") as f:
        csv.writer(f).writerows([["imagen", "clase_pred", "conf", "iou_misma_clase", "iou_otra_clase", "tipo"]] + filas)
    res[str(umbral)] = {"fp": len(filas), "tp": tp, "fn": fn, "tipos": Counter(x[5] for x in filas)}
met = m.val(data="/ext/sin_duplicados/limpio/data.yaml", split="test", conf=0.25,
            iou=0.5, batch=8, workers=2, plots=True, project="/ext/fp_analisis", name="cm", exist_ok=True, verbose=False)
res["matriz_confusion_ultralytics"] = met.confusion_matrix.matrix.tolist()
print(json.dumps(res, indent=1, default=int))
json.dump(res, open("/ext/fp_analisis/resumen.json", "w"), indent=1, default=int)
