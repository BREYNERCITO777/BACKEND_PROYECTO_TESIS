"""Copias aumentadas de una muestra del conjunto de ENTRENAMIENTO (nunca de
test) con motion blur y oclusion aleatorios, para el reentrenamiento v5.

Parametros aleatorios a proposito (angulo y tamano de blur, lado y fraccion de
oclusion) para no entrenar con exactamente la misma degradacion fija que usa
la evaluacion (generar_degradaciones.py: blur horizontal k=25, oclusion
izquierda 40%). El desenfoque gaussiano y la baja luz de la evaluacion no se
usan aqui en absoluto: sirven para medir si la mejora generaliza.
"""
import glob
import os
import random

import cv2
import numpy as np

random.seed(0)
np.random.seed(0)

FUENTES = {
    "propio": "/data/dataset_80_20/train/images",
    "zenodo": "/zenodo/images/train",
}
DESTINO = "/aug"
FRACCION = 0.30


def motion_blur_aleatorio(img):
    k = random.choice(range(9, 32, 2))
    kernel = np.zeros((k, k), np.float32)
    kernel[k // 2, :] = 1.0
    angulo = random.uniform(0, 180)
    rot = cv2.getRotationMatrix2D((k / 2 - 0.5, k / 2 - 0.5), angulo, 1.0)
    kernel = cv2.warpAffine(kernel, rot, (k, k))
    kernel /= max(kernel.sum(), 1e-6)
    return cv2.filter2D(img, -1, kernel)


def oclusion_aleatoria(img, cajas):
    if not cajas:
        return img
    out = img.copy()
    h, w = img.shape[:2]
    _, cx, cy, bw, bh = random.choice(cajas)
    x1, y1 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
    x2, y2 = int((cx + bw / 2) * w), int((cy + bh / 2) * h)
    f = random.uniform(0.2, 0.5)
    lado = random.choice(["izq", "der", "arr", "aba"])
    if lado == "izq":
        x2 = int(x1 + (x2 - x1) * f)
    elif lado == "der":
        x1 = int(x2 - (x2 - x1) * f)
    elif lado == "arr":
        y2 = int(y1 + (y2 - y1) * f)
    else:
        y1 = int(y2 - (y2 - y1) * f)
    color = tuple(int(c) for c in np.random.randint(0, 256, 3))
    cv2.rectangle(out, (x1, y1), (x2, y2), color, -1)
    return out


def leer_cajas(txt):
    if not os.path.exists(txt):
        return []
    cajas = []
    for linea in open(txt):
        p = linea.split()
        if len(p) >= 5:
            cajas.append((int(p[0]), *map(float, p[1:5])))
    return cajas


os.makedirs(f"{DESTINO}/images/train", exist_ok=True)
os.makedirs(f"{DESTINO}/labels/train", exist_ok=True)

conteo = {"blur": 0, "oclusion": 0, "ambos": 0}
for fuente, carpeta in FUENTES.items():
    imagenes = sorted(glob.glob(f"{carpeta}/*.*"))
    muestra = random.sample(imagenes, int(len(imagenes) * FRACCION))
    print(f"{fuente}: {len(muestra)} de {len(imagenes)} imagenes")
    for ruta in muestra:
        img = cv2.imread(ruta)
        if img is None:
            continue
        base = os.path.splitext(os.path.basename(ruta))[0]
        txt = ruta.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        cajas = leer_cajas(txt)

        tipo = random.choice(["blur", "oclusion", "ambos"]) if cajas else "blur"
        if tipo in ("oclusion", "ambos"):
            img = oclusion_aleatoria(img, cajas)
        if tipo in ("blur", "ambos"):
            img = motion_blur_aleatorio(img)
        conteo[tipo] += 1

        nombre = f"aug_{fuente}_{base}"
        cv2.imwrite(f"{DESTINO}/images/train/{nombre}.jpg", img)
        with open(f"{DESTINO}/labels/train/{nombre}.txt", "w") as f:
            f.write("".join(
                f"{c} {x} {y} {bw} {bh}\n" for c, x, y, bw, bh in cajas
            ))

print("Aumentos generados:", conteo)
