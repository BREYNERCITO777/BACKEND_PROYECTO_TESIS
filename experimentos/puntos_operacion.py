"""Puntos de operación a nivel de imagen (Reviewer 1, punto 5: "operating
points for different use cases"): para cada umbral, qué fracción de imágenes
con arma dispara alerta y qué fracción sin arma da falsa alarma. Se infiere una
vez por imagen y se barren los umbrales sobre la confianza máxima."""
import glob
import json
import os

from ultralytics import YOLO

BASE = "/data/limpio"
m = YOLO("/modelo/best.pt")
con, sin = [], []
for img in sorted(glob.glob(f"{BASE}/images/test/*.jpg")):
    lbl = f"{BASE}/labels/test/{os.path.basename(img)[:-4]}.txt"
    tiene = os.path.exists(lbl) and open(lbl).read().strip() != ""
    cajas = m(img, conf=0.05, verbose=False)[0].boxes
    maxc = max((float(b.conf[0]) for b in cajas), default=0.0)
    (con if tiene else sin).append(maxc)

filas = []
for u in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
    filas.append({
        "umbral": u,
        "alerta_con_arma": round(sum(c >= u for c in con) / len(con), 4),
        "falsa_alarma_sin_arma": round(sum(c >= u for c in sin) / len(sin), 4),
    })
    print(filas[-1])
json.dump({"con_arma": len(con), "sin_arma": len(sin), "puntos": filas},
          open("/salida/puntos_operacion.json", "w"), indent=2)
