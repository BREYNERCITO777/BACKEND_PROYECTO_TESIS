"""Busca en la fuente de pistolas (prefijo `armas`) las imagenes con alguna caja
de arma_blanca y las dibuja con sus etiquetas (docs/anotacion/). Resultado: en
las 4 el cuchillo esta bien anotado, pero la pistola visible no tiene caja.

Uso: docker run --rm -v tesis-dataset:/data:ro -v <salida>:/s tesis-backend:local \
       python anotaciones_incompletas.py
"""
import glob
import os

import cv2

hallazgos = []
for particion in ("train", "val"):
    for t in glob.glob(f"/data/dataset_80_20/{particion}/labels/armas*.txt"):
        filas = [l.split() for l in open(t).read().splitlines() if l.strip()]
        if any(f[0] == "1" for f in filas):
            hallazgos.append((particion, t, filas))
print(len(hallazgos), "imagenes")

mosaico = []
for particion, t, filas in hallazgos:
    base = os.path.basename(t)[:-4]
    img = cv2.imread(glob.glob(f"/data/dataset_80_20/{particion}/images/{base}.*")[0])
    h, w = img.shape[:2]
    for c, cx, cy, bw, bh in [list(map(float, f)) for f in filas]:
        color = (0, 0, 255) if c == 1 else (0, 200, 0)
        x1, y1 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
        cv2.rectangle(img, (x1, y1), (int((cx + bw / 2) * w), int((cy + bh / 2) * h)), color, 3)
        cv2.putText(img, "bladed" if c == 1 else "firearm", (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    print(particion, base, filas)
    mosaico.append(cv2.resize(img, (320, 320)))
cv2.imwrite("/s/anotaciones_incompletas.jpg", cv2.hconcat(mosaico))
