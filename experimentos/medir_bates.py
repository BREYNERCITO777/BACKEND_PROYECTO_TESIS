"""Tasa de falsos positivos sobre imagenes de test que SOLO contienen un bate,
al umbral de operacion real (0.65) y al de evaluacion (0.25)."""
import os
from ultralytics import YOLO

m = YOLO("/modelo/best.pt")
LBL = "/zenodo_orig/labels/test"
IMG = "/zenodo_orig/images/test"

solo_bate = []
for f in sorted(os.listdir(LBL)):
    clases = {int(l.split()[0]) for l in open(os.path.join(LBL, f)) if l.strip()}
    if clases == {2}:
        solo_bate.append(os.path.join(IMG, f.replace(".txt", ".jpg")))

print(f"Imagenes de test con SOLO bate: {len(solo_bate)}")
for umbral in (0.25, 0.65):
    con_fp = 0
    por_clase = {}
    for ruta in solo_bate:
        r = m(ruta, conf=umbral, verbose=False)[0]
        if len(r.boxes):
            con_fp += 1
            for b in r.boxes:
                n = m.names[int(b.cls[0])]
                por_clase[n] = por_clase.get(n, 0) + 1
    print(f"umbral {umbral}: {con_fp}/{len(solo_bate)} imagenes con falso positivo "
          f"({100*con_fp/len(solo_bate):.1f}%)  cajas por clase: {por_clase}")
