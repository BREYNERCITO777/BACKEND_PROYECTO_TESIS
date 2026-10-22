"""Desempeño a nivel de imagen, al umbral de operación (0.65): lo que decide si
el sistema alerta. La métrica por cajas (IoU >= 0.5) cuenta como error un arma
detectada con la caja desplazada; aquí basta con que la imagen dispare alerta."""
import glob
import json
import os

from ultralytics import YOLO

UMBRAL = 0.65
BASE = "/data/limpio"
m = YOLO("/modelo/best.pt")

con_arma = alertan_con_arma = sin_arma = alertan_sin_arma = 0
por_clase = {"arma_fuego": [0, 0], "arma_blanca": [0, 0]}  # [imagenes, con alerta]
for img in sorted(glob.glob(f"{BASE}/images/test/*.jpg")):
    lbl = f"{BASE}/labels/test/{os.path.basename(img)[:-4]}.txt"
    clases = {int(l.split()[0]) for l in open(lbl) if l.strip()} if os.path.exists(lbl) else set()
    alerta = len(m(img, conf=UMBRAL, verbose=False)[0].boxes) > 0
    if clases:
        con_arma += 1
        alertan_con_arma += alerta
        for c in clases:
            nombre = m.names[c]
            por_clase[nombre][0] += 1
            por_clase[nombre][1] += alerta
    else:
        sin_arma += 1
        alertan_sin_arma += alerta

r = {
    "umbral": UMBRAL,
    "imagenes_con_arma": con_arma,
    "tasa_alerta_con_arma": round(alertan_con_arma / con_arma, 4),
    "imagenes_sin_arma": sin_arma,
    "tasa_falsa_alarma_sin_arma": round(alertan_sin_arma / sin_arma, 4),
    "tasa_alerta_por_clase": {k: round(v[1] / v[0], 4) for k, v in por_clase.items()},
}
print(json.dumps(r, indent=2))
json.dump(r, open("/salida/nivel_imagen.json", "w"), indent=2)
