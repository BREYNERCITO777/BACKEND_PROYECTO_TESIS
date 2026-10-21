"""Genera versiones degradadas del test externo (Reviewer 1, punto 5):
motion blur, compresion JPEG agresiva, y oclusion parcial sobre las cajas
reales. Mismas etiquetas que el original -solo cambia la imagen- para poder
evaluar v4 directamente con el mismo data.yaml.
"""
import os
import shutil
import random
import cv2
import numpy as np

ORIGEN_IMG = "/data/eval_dataset/images/test"
ORIGEN_LBL = "/data/eval_dataset/labels/test"
BASE = "/data/degradaciones"

random.seed(0)


def motion_blur(img, k=25):
    kernel = np.zeros((k, k))
    kernel[(k - 1) // 2, :] = np.ones(k)
    kernel /= k
    return cv2.filter2D(img, -1, kernel)


def compresion_agresiva(img, calidad=10):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, calidad])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def ocluir_cajas(img, txt_path, fraccion=0.4):
    h, w = img.shape[:2]
    if not os.path.exists(txt_path):
        return img
    out = img.copy()
    for linea in open(txt_path):
        p = linea.split()
        if len(p) < 5:
            continue
        cx, cy, bw, bh = float(p[1]) * w, float(p[2]) * h, float(p[3]) * w, float(p[4]) * h
        x1, y1 = int(cx - bw / 2), int(cy - bh / 2)
        x2, y2 = int(cx + bw / 2), int(cy + bh / 2)
        # Tapar una franja del lado izquierdo de la caja (oclusion parcial)
        ox2 = int(x1 + (x2 - x1) * fraccion)
        cv2.rectangle(out, (x1, y1), (ox2, y2), (0, 0, 0), -1)
    return out


DEGRADACIONES = {
    "blur": lambda img, txt: motion_blur(img, 25),
    "compresion": lambda img, txt: compresion_agresiva(img, 10),
    "oclusion": lambda img, txt: ocluir_cajas(img, txt, 0.4),
}

archivos = sorted(os.listdir(ORIGEN_IMG))
print(f"{len(archivos)} imagenes a degradar x {len(DEGRADACIONES)} degradaciones")

for nombre_deg, func in DEGRADACIONES.items():
    img_dst = f"{BASE}/{nombre_deg}/images/test"
    lbl_dst = f"{BASE}/{nombre_deg}/labels/test"
    os.makedirs(img_dst, exist_ok=True)
    os.makedirs(lbl_dst, exist_ok=True)

    for nombre in archivos:
        ruta_img = os.path.join(ORIGEN_IMG, nombre)
        base_nombre = os.path.splitext(nombre)[0]
        ruta_txt = os.path.join(ORIGEN_LBL, base_nombre + ".txt")

        img = cv2.imread(ruta_img)
        if img is None:
            continue
        img_deg = func(img, ruta_txt)
        cv2.imwrite(os.path.join(img_dst, nombre), img_deg)

        if os.path.exists(ruta_txt):
            shutil.copy(ruta_txt, os.path.join(lbl_dst, base_nombre + ".txt"))
        else:
            open(os.path.join(lbl_dst, base_nombre + ".txt"), "w").close()

    with open(f"{BASE}/{nombre_deg}/data.yaml", "w") as f:
        f.write(
            f"path: /data/degradaciones/{nombre_deg}\n"
            "test: images/test\ntrain: images/test\nval: images/test\n"
            "nc: 2\nnames: ['arma_fuego', 'arma_blanca']\n"
        )
    print(f"  {nombre_deg}: listo")

print("Listo.")
