"""Segunda pasada sobre los candidatos de duplicados_phash.py: el dHash de 64
bits confunde fotos de producto con la misma composicion. Para cada par
candidato se compara la imagen en escala de grises a 64x64 (diferencia
absoluta media, 0-255). Un duplicado real (misma foto, recomprimida o
redimensionada) da valores muy bajos."""
import json
import os

import cv2
import numpy as np

CARPETAS = {
    "zenodo_train": "/zenodo_orig/images/train",
    "zenodo_val": "/zenodo_orig/images/val",
    "propio_train": "/data/dataset_80_20/train/images",
    "propio_val": "/data/dataset_80_20/val/images",
}


def norm(ruta):
    img = cv2.imread(ruta, cv2.IMREAD_GRAYSCALE)
    return cv2.resize(img, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)


d = json.load(open("/salida/duplicados_test_externo.json"))
resultado = {}
for t, candidatos in d["detalle"].items():
    a = norm(f"/zenodo_orig/images/test/{t}")
    mejor = None
    for c in candidatos:
        b = norm(os.path.join(CARPETAS[c["conjunto"]], c["archivo"]))
        mad = float(np.abs(a - b).mean())
        if mejor is None or mad < mejor["mad"]:
            mejor = {**c, "mad": round(mad, 2)}
    resultado[t] = mejor

mads = sorted(r["mad"] for r in resultado.values())
hist = np.histogram(mads, bins=[0, 2, 4, 6, 8, 10, 15, 20, 30, 50, 255])
print("Histograma de diferencia media (0-255) del mejor candidato por imagen de test:")
for n, (lo, hi) in zip(hist[0], zip(hist[1][:-1], hist[1][1:])):
    print(f"  [{lo:>3.0f}, {hi:>3.0f}): {n}")

with open("/salida/duplicados_verificados.json", "w") as f:
    json.dump(resultado, f, indent=2)
