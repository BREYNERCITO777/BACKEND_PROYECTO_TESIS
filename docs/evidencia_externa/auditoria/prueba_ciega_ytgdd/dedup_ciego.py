"""Comprueba que ninguna imagen del test de YouTube-GDD (500) sea copia de algo
que v5 vio al entrenar: mismo dHash de 64 bits y umbral de Hamming 6 que el
articulo (experimentos/duplicados_phash.py)."""
import glob
import json
import os
from concurrent.futures import ProcessPoolExecutor

import cv2

UMBRAL = 6
TEST = "/ciego/ytgdd_test/images/test"
FUENTES = {
    "propio_train": "/data/dataset_80_20/train/images",
    "propio_val": "/data/dataset_80_20/val/images",
    "fondos": "/data/fondos",
    "zenodo_train": "/zen/train_dataset/images/train",
    "zenodo_val": "/zen/train_dataset/images/val",
    "copias_aumentadas_v5": "/zen/aug_dataset/images/train",
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


def imagenes(c):
    return sorted(p for p in glob.glob(f"{c}/**/*", recursive=True)
                  if p.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")))


ht = hashear(imagenes(TEST))
print("test:", len(ht))
res, conteo = {}, {}
for nombre, carpeta in FUENTES.items():
    h = hashear(imagenes(carpeta))
    conteo[nombre] = len(h)
    print(nombre, len(h), flush=True)
    for rt, a in ht.items():
        for re_, b in h.items():
            if bin(a ^ b).count("1") <= UMBRAL:
                res.setdefault(os.path.basename(rt), []).append([nombre, os.path.basename(re_), bin(a ^ b).count("1")])
json.dump({"umbral": UMBRAL, "test": len(ht), "fuentes": conteo, "candidatos": res},
          open("/ciego/dedup_ciego.json", "w"), indent=1)
print("imagenes de test con candidato a duplicado:", len(res))
for k, v in list(res.items())[:10]:
    print(k, v[:2])
