"""Aplica el mismo dHash + umbral 6 del script original (duplicados_phash.py)
pero solo a los 24 archivos .JPG (mayuscula) del test de Zenodo que el glob
case-sensitive se salto. Compara contra las mismas cuatro fuentes de
entrenamiento. Imprime si cada uno es duplicado o no.
"""
import glob
import json
import os
from concurrent.futures import ProcessPoolExecutor

import cv2

UMBRAL = 6
TEST_JPG = "/zenodo_orig/images/test"
ENTRENAMIENTO = {
    "propio_train": "/data/dataset_80_20/train/images",
    "propio_val": "/data/dataset_80_20/val/images",
    "zenodo_train": "/zenodo_orig_full/images/train",
    "zenodo_val": "/zenodo_orig_full/images/val",
}


def dhash(ruta):
    img = cv2.imread(ruta, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return ruta, None
    peq = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (peq[:, 1:] > peq[:, :-1]).flatten()
    return ruta, int("".join("1" if b else "0" for b in bits), 2)


def hashear(rutas):
    with ProcessPoolExecutor() as ex:
        return {r: h for r, h in ex.map(dhash, rutas, chunksize=64) if h is not None}


def popcount(x):
    return bin(x).count("1")


objetivo = sorted(glob.glob(f"{TEST_JPG}/*.JPG"))
print(f"archivos .JPG encontrados: {len(objetivo)}")
hash_objetivo = hashear(objetivo)

resultado = {}
for nombre_fuente, carpeta in ENTRENAMIENTO.items():
    rutas = sorted(glob.glob(f"{carpeta}/*.*"))
    print(f"{nombre_fuente}: {len(rutas)} imagenes a comparar")
    hashes = hashear(rutas)
    for ruta_t, h_t in hash_objetivo.items():
        base = os.path.basename(ruta_t)
        for ruta_e, h_e in hashes.items():
            if popcount(h_t ^ h_e) <= UMBRAL:
                resultado.setdefault(base, []).append((nombre_fuente, os.path.basename(ruta_e),
                                                         popcount(h_t ^ h_e)))

print("=" * 60)
print(f"duplicados encontrados entre los 24: {len(resultado)}")
for base, coincidencias in resultado.items():
    print(base, "->", coincidencias[:3])

limpios = [os.path.basename(r) for r in objetivo if os.path.basename(r) not in resultado]
print(f"limpios (sin duplicado, se pueden agregar al test): {len(limpios)}")
with open("/zenodo_orig/jpg24_resultado.json", "w") as f:
    json.dump({"duplicados": resultado, "limpios": limpios}, f, indent=2)
