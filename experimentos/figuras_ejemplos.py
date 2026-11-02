"""Figuras 10 y 13 en su version final: imagenes del test depurado SIN marca de
agua de bancos de imagenes, caras difuminadas, clases en ingles y paneles
(A), (B)...; 180 mm de ancho a 300 dpi.

Figura 10: errores reales de v5 a conf 0.25 (fp_analisis/errores_por_imagen.json,
generado por candidatos_fig10.py).
Figura 13: las mismas cuatro imagenes de la comparacion cualitativa
(predicciones_cualitativas.json, de figura_cualitativa.py --predecir).

Uso (dentro de sentinel-backend:1.0.0, con /ext = dataset_externo_zenodo y
/repo = el repositorio): python /repo/experimentos/figuras_ejemplos.py
"""
import json

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

TEST = "/ext/sin_duplicados/limpio/images/test"
BAJA = "/ext/sin_duplicados/baja_luz/images/test"
SALIDA = "/repo/docs/figuras_articulo/final"
ANCHO = 180 / 25.4
CLASE = {0: "firearm", 1: "bladed"}
ROJO, NARANJA, VERDE = (40, 40, 220), (0, 140, 255), (60, 170, 40)  # BGR
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

CARAS = [cv2.CascadeClassifier(cv2.data.haarcascades + n)
         for n in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
# Caras que el detector automatico no encuentra (perfil, oclusion), revisadas a ojo:
# archivo -> lista de (x1, y1, x2, y2) en fraccion del ancho/alto de la imagen.
CARAS_MANUALES = json.load(open("/repo/experimentos/caras_manuales.json"))


def difuminar_caras(img, archivo):
    h, w = img.shape[:2]
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cajas = []
    for cc in CARAS:
        for flip in (False, True):
            g = cv2.flip(gris, 1) if flip else gris
            for (x, y, bw, bh) in cc.detectMultiScale(g, 1.1, 5, minSize=(max(12, w // 60),) * 2):
                if flip:
                    x = w - x - bw
                cajas.append((x, y, x + bw, y + bh))
    for fx1, fy1, fx2, fy2 in CARAS_MANUALES.get(archivo, []):
        cajas.append((int(fx1 * w), int(fy1 * h), int(fx2 * w), int(fy2 * h)))
    for x1, y1, x2, y2 in cajas:
        mx, my = int((x2 - x1) * 0.25), int((y2 - y1) * 0.25)
        x1, y1, x2, y2 = max(0, x1 - mx), max(0, y1 - my), min(w, x2 + mx), min(h, y2 + my)
        roi = img[y1:y2, x1:x2]
        k = max(15, (min(roi.shape[:2]) // 2) | 1)
        img[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)
    return img, len(cajas)


def caja(img, b, color, texto, punteada=False):
    x1, y1, x2, y2 = map(int, b)
    grosor = max(2, img.shape[1] // 260)
    if punteada:
        paso = grosor * 5
        for k in range(x1, x2, paso * 2):
            for y in (y1, y2):
                cv2.line(img, (k, y), (min(k + paso, x2), y), color, grosor)
        for k in range(y1, y2, paso * 2):
            for x in (x1, x2):
                cv2.line(img, (x, k), (x, min(k + paso, y2)), color, grosor)
    else:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, grosor)
    if texto:
        esc = img.shape[1] / 1100
        (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, esc, max(1, grosor // 2))
        ya = max(th + 6, y1)
        xt = max(0, min(x1, img.shape[1] - tw - 6))
        cv2.rectangle(img, (xt, ya - th - 6), (xt + tw + 6, ya), color, -1)
        cv2.putText(img, texto, (xt + 3, ya - 4), cv2.FONT_HERSHEY_SIMPLEX, esc, (255, 255, 255),
                    max(1, grosor // 2), cv2.LINE_AA)


def rgb(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


registro = {}

# ---------------------------------------------------------------- Figura 10
err = json.load(open("/ext/fp_analisis/errores_por_imagen.json"))
F10 = [("1f929c1b-1434.jpg", "(A) Missed: firearm in\nlow-resolution CCTV"),
       ("09a31ac4-1086.jpg", "(B) Missed: machete under\nstrong red light"),
       ("0f3678c1-1615.jpg", "(C) Missed: uncommon\nsporting rifle"),
       ("17736cbb-0118.jpg", "(D) Missed: handgun\nseen end-on"),
       ("A6_9dec77ea-0065.jpg", "(E) False alarm:\nno weapon in the scene"),
       ("34a2076c-2935.jpg", "(F) Detected with a displaced\nbox (counted as an error)")]
fig, ejes = plt.subplots(2, 3, figsize=(ANCHO, 4.8))
for ax, (archivo, titulo) in zip(ejes.flat, F10):
    img = cv2.imread(f"{TEST}/{archivo}")
    img, n = difuminar_caras(img, archivo)
    registro[archivo] = n
    e = err[archivo]
    desplazada = archivo.startswith("34a2076c")
    for c, b in ([] if desplazada else e["fn"]):
        caja(img, b, ROJO, f"missed {CLASE[c]}")
    for c, conf, b, _ in e["fp"]:
        caja(img, b, NARANJA, f"{CLASE[c]} {conf:.2f}")
    if desplazada:
        for c, b in e["gt"]:
            caja(img, b, ROJO, "annotation", punteada=True)
    ax.imshow(rgb(img))
    ax.set_title(titulo, fontsize=8.5, loc="left", pad=3)
    ax.axis("off")
fig.legend(handles=[Line2D([], [], color="#dc2828", lw=2.5, label="Annotated weapon (missed; dashed in F)"),
                    Line2D([], [], color="#ff8c00", lw=2.5, label="Detection without a matching annotation")],
           loc="lower center", ncol=2, frameon=False, fontsize=8.5)
fig.tight_layout(rect=(0, 0.05, 1, 1))
for ext in ("png", "tiff"):
    fig.savefig(f"{SALIDA}/Figura_10.{ext}", dpi=300, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- Figura 13
pred = json.load(open("/ext/salida_cualitativa/predicciones_cualitativas.json"))
claves = json.load(open("/ext/salida_cualitativa/figura_cualitativa_claves.json"))["claves"]
MODELOS = [("v5", "v5 (YOLOv8s, deployed)", (52, 104, 235)), ("yolov5s", "YOLOv5s", (214, 120, 42)),
           ("frcnn", "Faster R-CNN", (60, 140, 60))]
FILAS = ["(A) CCTV-like scene:\nall three detect\nthe knife", "(B) Two knives:\nYOLOv5s misses one",
         "(C) Low light, sporting\nrifle: only Faster R-CNN\ndetects it",
         "(D) No weapon:\nYOLOv5s and Faster\nR-CNN raise false alarms"]
fig, ejes = plt.subplots(4, 3, figsize=(ANCHO, 6.6))
for i, clave in enumerate(claves):
    conjunto, archivo = clave.split("/", 1)
    base = cv2.imread(f"{TEST if conjunto == 'limpio' else BAJA}/{archivo}")
    base, n = difuminar_caras(base, archivo)
    registro[clave] = n
    for j, (m, nombre, color) in enumerate(MODELOS):
        img = base.copy()
        for g in pred[clave]["gt"]:
            caja(img, g[1:5], (255, 255, 255), "", punteada=True)
        for p in pred[clave][m]:
            caja(img, p[1:5], color, f"{CLASE[p[0]]} {p[5]:.2f}")
        ax = ejes[i, j]
        ax.imshow(rgb(img))
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        if i == 0:
            ax.set_title(nombre, fontsize=9.5, fontweight="bold", color=np.array(color[::-1]) / 255)
        if j == 0:
            ax.set_ylabel(FILAS[i], fontsize=8.5, rotation=0, ha="right", va="center", labelpad=8)
fig.legend(handles=[Line2D([], [], color="#555555", lw=2, ls=(0, (3, 2)), label="Annotated weapon"),
                    Line2D([], [], color="#333333", lw=2.5, label="Detection: class and confidence (threshold 0.5)")],
           loc="lower center", ncol=2, frameon=False, fontsize=8.5)
fig.tight_layout(rect=(0, 0.04, 1, 1))
for ext in ("png", "tiff"):
    fig.savefig(f"{SALIDA}/Figura_13.{ext}", dpi=300, facecolor="white")
plt.close(fig)
print("caras difuminadas por imagen:", registro)
