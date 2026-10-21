"""Dos degradaciones adicionales del test externo que NO se usan como aumento
en ningun entrenamiento: desenfoque gaussiano (camara fuera de foco) y baja
luz con ruido de sensor. Sirven para medir si la mejora de v5 generaliza o
solo memoriza el tipo de blur/oclusion con que se entreno."""
import os
import shutil

import cv2
import numpy as np

ORIGEN_IMG = "/data/eval_dataset/images/test"
ORIGEN_LBL = "/data/eval_dataset/labels/test"
BASE = "/data/degradaciones"
rng = np.random.default_rng(0)


def desenfoque(img):
    return cv2.GaussianBlur(img, (0, 0), sigmaX=4)


def baja_luz(img):
    oscuro = img.astype(np.float32) * 0.25
    ruido = rng.normal(0, 8, img.shape)
    return np.clip(oscuro + ruido, 0, 255).astype(np.uint8)


for nombre, func in {"desenfoque": desenfoque, "baja_luz": baja_luz}.items():
    img_dst = f"{BASE}/{nombre}/images/test"
    lbl_dst = f"{BASE}/{nombre}/labels/test"
    os.makedirs(img_dst, exist_ok=True)
    os.makedirs(lbl_dst, exist_ok=True)
    for archivo in sorted(os.listdir(ORIGEN_IMG)):
        img = cv2.imread(os.path.join(ORIGEN_IMG, archivo))
        if img is None:
            continue
        cv2.imwrite(os.path.join(img_dst, archivo), func(img))
        txt = os.path.splitext(archivo)[0] + ".txt"
        origen_txt = os.path.join(ORIGEN_LBL, txt)
        if os.path.exists(origen_txt):
            shutil.copy(origen_txt, os.path.join(lbl_dst, txt))
        else:
            open(os.path.join(lbl_dst, txt), "w").close()
    with open(f"{BASE}/{nombre}/data.yaml", "w") as f:
        f.write(
            f"path: /data/degradaciones/{nombre}\n"
            "test: images/test\ntrain: images/test\nval: images/test\n"
            "nc: 2\nnames: ['arma_fuego', 'arma_blanca']\n"
        )
    print(f"{nombre}: listo")
