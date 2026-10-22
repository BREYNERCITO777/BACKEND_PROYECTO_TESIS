"""Angulo de camara (Reviewer 1, punto 5: "varied camera angles").

Simula, sobre el test externo sin duplicados, dos montajes de camara con una
transformacion de perspectiva fija:
  - elevada: camara alta que mira hacia abajo; el borde superior se angosta
    un 20% de cada lado y la imagen se acorta verticalmente al 80%.
  - lateral: camara de costado; el borde izquierdo se acorta un 20% arriba y
    abajo y la imagen se angosta horizontalmente al 80%.
Las cajas pasan a ser el rectangulo que contiene sus cuatro esquinas
proyectadas (con estos angulos quedan apenas mas holgadas que el objeto).
Ningun entrenamiento uso estas transformaciones.

Uso (dentro del contenedor, test en /ext): python generar_angulos.py
"""
import os

import cv2
import numpy as np

ORIGEN = "/ext/sin_duplicados/limpio"
BASE = "/ext/sin_duplicados"


def destino(nombre, w, h):
    if nombre == "elevada":   # borde superior mas corto, imagen aplastada en vertical
        return np.float32([[0.2 * w, 0.2 * h], [0.8 * w, 0.2 * h], [w, h], [0, h]])
    return np.float32([[0.2 * w, 0.2 * h], [w, 0], [w, h], [0.2 * w, 0.8 * h]])  # lateral


def transformar(nombre, img, filas):
    h, w = img.shape[:2]
    origen = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(origen, destino(nombre, w, h))
    salida = cv2.warpPerspective(img, M, (w, h), borderValue=(0, 0, 0))
    nuevas = []
    for c, cx, cy, bw, bh in filas:
        x1, y1, x2, y2 = (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h
        esquinas = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]).reshape(-1, 1, 2)
        p = cv2.perspectiveTransform(esquinas, M).reshape(-1, 2)
        a1, b1 = np.clip(p.min(0), 0, [w, h])
        a2, b2 = np.clip(p.max(0), 0, [w, h])
        if a2 - a1 >= 2 and b2 - b1 >= 2:
            nuevas.append(f"{int(c)} {(a1 + a2) / 2 / w:.6f} {(b1 + b2) / 2 / h:.6f} "
                          f"{(a2 - a1) / w:.6f} {(b2 - b1) / h:.6f}")
    return salida, nuevas


for nombre in ("elevada", "lateral"):
    img_dst, lbl_dst = f"{BASE}/{nombre}/images/test", f"{BASE}/{nombre}/labels/test"
    os.makedirs(img_dst, exist_ok=True)
    os.makedirs(lbl_dst, exist_ok=True)
    for archivo in sorted(os.listdir(f"{ORIGEN}/images/test")):
        img = cv2.imread(f"{ORIGEN}/images/test/{archivo}")
        if img is None:
            continue
        txt = os.path.splitext(archivo)[0] + ".txt"
        ruta_txt = f"{ORIGEN}/labels/test/{txt}"
        filas = [list(map(float, l.split())) for l in open(ruta_txt).read().splitlines()
                 if len(l.split()) == 5] if os.path.exists(ruta_txt) else []
        salida, nuevas = transformar(nombre, img, filas)
        cv2.imwrite(f"{img_dst}/{archivo}", salida)
        with open(f"{lbl_dst}/{txt}", "w") as f:
            f.write("\n".join(nuevas))
    with open(f"{BASE}/{nombre}/data.yaml", "w") as f:
        f.write(f"path: {BASE}/{nombre}\ntest: images/test\ntrain: images/test\nval: images/test\n"
                "nc: 2\nnames: ['arma_fuego', 'arma_blanca']\n")
    print(nombre, "listo", flush=True)
