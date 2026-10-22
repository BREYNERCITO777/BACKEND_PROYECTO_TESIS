"""Video corto para la demo del repositorio: 60 imagenes del test externo sin
duplicados (Dangerous Items, Zenodo, CC BY 4.0), 40 con armas y 20 sin, a
2 FPS (30 s). Lo bastante chico para versionarse."""
import glob
import os
import random

import cv2

random.seed(0)
BASE = "/w/sin_duplicados/limpio"
con, sin = [], []
for img in sorted(glob.glob(f"{BASE}/images/test/*.jpg")):
    lbl = f"{BASE}/labels/test/" + os.path.basename(img)[:-4] + ".txt"
    (con if os.path.exists(lbl) and open(lbl).read().strip() else sin).append(img)

elegidas = random.sample(con, 40) + random.sample(sin, 20)
random.shuffle(elegidas)

salida = cv2.VideoWriter("/w/video_demo.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 2, (960, 540))
for ruta in elegidas:
    salida.write(cv2.resize(cv2.imread(ruta), (960, 540)))
salida.release()
with open("/w/video_demo_fuentes.txt", "w") as f:
    f.write("\n".join(os.path.basename(r) for r in elegidas) + "\n")
print(f"{len(elegidas)} imagenes, {os.path.getsize('/w/video_demo.mp4') / 1e6:.1f} MB")
