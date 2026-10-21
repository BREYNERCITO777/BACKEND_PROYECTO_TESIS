"""Busca imagenes del test externo (Zenodo) que tambien esten -aunque sea
recomprimidas o redimensionadas- en algun conjunto de entrenamiento: el propio
(Kaggle/DatasetNinja) o el train/val de Zenodo. Si las hay, el mAP del test
externo esta inflado. Usa dHash de 64 bits; distancia de Hamming <= UMBRAL se
considera la misma foto."""
import glob
import json
import os
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

UMBRAL = 6
TEST = "/zenodo_orig/images/test"
ENTRENAMIENTO = {
    "propio_train": "/data/dataset_80_20/train/images",
    "propio_val": "/data/dataset_80_20/val/images",
    "zenodo_train": "/zenodo_orig/images/train",
    "zenodo_val": "/zenodo_orig/images/val",
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


test = hashear(sorted(glob.glob(f"{TEST}/*.jpg")))
print(f"test externo: {len(test)} imagenes", flush=True)
test_items = list(test.items())
test_arr = np.array([h for _, h in test_items], dtype=np.uint64)

coincidencias = {}
for nombre, carpeta in ENTRENAMIENTO.items():
    entren = hashear(sorted(glob.glob(f"{carpeta}/*.*")))
    print(f"{nombre}: {len(entren)} imagenes hasheadas", flush=True)
    for ruta_e, h_e in entren.items():
        dist = np.array([popcount(int(x)) for x in np.bitwise_xor(test_arr, np.uint64(h_e))])
        for idx in np.where(dist <= UMBRAL)[0]:
            ruta_t = test_items[idx][0]
            coincidencias.setdefault(os.path.basename(ruta_t), []).append(
                {"conjunto": nombre, "archivo": os.path.basename(ruta_e), "distancia": int(dist[idx])}
            )

por_conjunto = {}
for lista in coincidencias.values():
    for c in {c["conjunto"] for c in lista}:
        por_conjunto[c] = por_conjunto.get(c, 0) + 1

print(f"\nImagenes de test con un posible duplicado en entrenamiento: {len(coincidencias)} de {len(test)}")
print("Por conjunto:", por_conjunto)
with open("/salida/duplicados_test_externo.json", "w") as f:
    json.dump({"umbral_hamming": UMBRAL, "total_test": len(test),
               "test_con_duplicado": len(coincidencias), "por_conjunto": por_conjunto,
               "detalle": coincidencias}, f, indent=2)
