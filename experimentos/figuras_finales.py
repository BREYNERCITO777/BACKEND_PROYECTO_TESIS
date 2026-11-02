"""Figuras 8, 9, 11 y 12 en el formato final de Frontiers: 180 mm de ancho,
300 dpi, RGB, texto de al menos 8 pt y paneles (A), (B).

- Figura 8: matriz de confusion de v5 (conf 0.25) de la misma corrida que la
  Tabla 4 (batch 8), clases en ingles; normalizada (A) y en conteos (B).
- Figura 9: curvas de entrenamiento de v5 desde su results.csv.
- Figura 11: curvas precision-recall de v5 con los puntos de operacion; cada
  curva se distingue tambien por el tipo de linea.
- Figura 12: precision frente a latencia (Tabla 4); etiquetas sin cruzar la
  linea de 200 ms.

Uso: python experimentos/figuras_finales.py  (desde la raiz del repositorio)
"""
import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

SALIDA = "docs/figuras_articulo/final"
ANCHO = 180 / 25.4  # pulgadas
TINTA, TINTA2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
AZUL, NARANJA = "#2a78d6", "#eb6834"  # paleta categorica validada
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": TINTA2,
                     "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
                     "axes.titlesize": 9.5, "legend.fontsize": 8.5})
os.makedirs(SALIDA, exist_ok=True)


def guardar(fig, nombre):
    """PNG y TIFF RGB (sin canal alfa) a 300 dpi."""
    from PIL import Image
    fig.savefig(f"{SALIDA}/{nombre}.png", dpi=300, facecolor="white")
    plt.close(fig)
    im = Image.open(f"{SALIDA}/{nombre}.png").convert("RGB")
    im.save(f"{SALIDA}/{nombre}.png", dpi=(300, 300))
    im.save(f"{SALIDA}/{nombre}.tiff", dpi=(300, 300), compression="tiff_lzw")


def limpiar(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


# ---------------------------------------------------------------- Figura 8
cm = np.array(json.load(open("docs/evidencia_externa/auditoria/fp_analisis/resumen.json"))
              ["matriz_confusion_ultralytics"])  # filas = prediccion, columnas = clase verdadera
nombres = ["Firearm", "Bladed\nweapon", "Background"]
norm = cm / np.where(cm.sum(0) == 0, 1, cm.sum(0))
fig, ejes = plt.subplots(1, 2, figsize=(ANCHO, 3.35))
for ax, datos, titulo, fmt in [(ejes[0], norm, "(A) Normalized over the true class", "{:.2f}"),
                               (ejes[1], cm, "(B) Absolute counts", "{:.0f}")]:
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            v = datos[i, j]
            texto = "" if (i == 2 and j == 2) else fmt.format(v)
            ax.text(j, i, texto, ha="center", va="center", fontsize=10,
                    color="white" if norm[i, j] > 0.55 else TINTA)
    ax.set_xticks(range(3), nombres)
    ax.set_yticks(range(3), nombres)
    ax.set_xlabel("True class")
    ax.set_ylabel("Predicted class")
    ax.set_title(titulo, loc="left", color=TINTA)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
fig.tight_layout()
guardar(fig, "Figura_08")

# ---------------------------------------------------------------- Figura 9
filas = list(csv.DictReader(open("docs/evidencia_externa/v5/results_v5.csv")))
col = lambda k: np.array([float(f[k]) for f in filas])  # noqa: E731
ep = col("epoch")
fig, ejes = plt.subplots(2, 2, figsize=(ANCHO, 5.0), sharex=True)
paneles = [
    (ejes[0, 0], "(A) Training loss", [("train/box_loss", "Box", "-"), ("train/cls_loss", "Class", "--"),
                                       ("train/dfl_loss", "DFL", "-.")]),
    (ejes[0, 1], "(B) Validation loss", [("val/box_loss", "Box", "-"), ("val/cls_loss", "Class", "--"),
                                         ("val/dfl_loss", "DFL", "-.")]),
    (ejes[1, 0], "(C) Precision and recall", [("metrics/precision(B)", "Precision", "-"),
                                              ("metrics/recall(B)", "Recall", "--")]),
    (ejes[1, 1], "(D) mAP", [("metrics/mAP50(B)", "mAP@0.5", "-"), ("metrics/mAP50-95(B)", "mAP@0.5:0.95", "--")]),
]
colores = [AZUL, NARANJA, TINTA2]
for ax, titulo, series in paneles:
    for (k, etiqueta, ls), c in zip(series, colores):
        ax.plot(ep, col(k), ls=ls, color=c, lw=1.8, label=etiqueta)
    ax.set_title(titulo, loc="left", color=TINTA)
    ax.grid(color=REJILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    limpiar(ax)
for ax in ejes[1]:
    ax.set_xlabel("Epoch of the v5 fine-tuning stage")
    ax.set_xticks(range(0, int(ep.max()) + 1, 5))
fig.tight_layout()
guardar(fig, "Figura_09")

# ---------------------------------------------------------------- Figura 11
d = json.load(open("docs/evidencia_externa/v5/curvas_pr_v5.json"))
x, y = np.array(d["pr_x"]), np.array(d["pr_y"])
cx, P, R = np.array(d["conf_x"]), np.array(d["p_conf"]), np.array(d["r_conf"])
fig, ax = plt.subplots(figsize=(ANCHO, 3.7))
ax.plot(x, y[0], color=AZUL, lw=1.6, ls="-", label=f"Firearm (AP@0.5 {d['ap50'][0]:.3f})")
ax.plot(x, y[1], color=NARANJA, lw=1.6, ls="--", label=f"Bladed weapon (AP@0.5 {d['ap50'][1]:.3f})")
ax.plot(x, y.mean(0), color=TINTA, lw=2.4, ls="-.", label=f"Both classes (mAP@0.5 {d['map50']:.3f})")
for c, lab, pos in [(0.70, "0.70", (0.52, 0.86)), (0.65, "0.65 (default)", (0.52, 0.79)),
                    (0.50, "0.50", (0.52, 0.72))]:
    i = np.abs(cx - c).argmin()
    p, r = P[:, i].mean(), R[:, i].mean()
    ax.plot(r, p, "o", color=TINTA, ms=6, zorder=5, markeredgecolor="white")
    ax.annotate(f"conf {lab}: P {p:.2f}, R {r:.2f}", (r, p), pos, fontsize=8.5, color=TINTA, ha="right",
                va="center", arrowprops=dict(arrowstyle="-", color=TINTA2, lw=0.8, shrinkA=2, relpos=(1, 0.5)))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.02)
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.grid(color=REJILLA, lw=0.8)
ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False)
limpiar(ax)
fig.tight_layout()
guardar(fig, "Figura_11")

# ---------------------------------------------------------------- Figura 12
MODELOS = [("YOLOv8n", "yolo", 0.795, 13.6, 53.7), ("YOLOv5s", "yolo", 0.838, 17.7, 98.4),
           ("YOLOv8s", "yolo", 0.854, 16.4, 128.7), ("v5 (deployed)", "v5", 0.859, 12.9, 119.4),
           ("Faster R-CNN", "frcnn", 0.864, 71.4, 2040.5)]
ESTILO = {"yolo": dict(color=AZUL, marker="o", label="YOLO from COCO weights"),
          "v5": dict(color=NARANJA, marker="D", label="Deployed model (YOLOv8s, v5)"),
          "frcnn": dict(color=TINTA2, marker="s", label="Faster R-CNN (two-stage)")}
ETIQ = {"gpu": {"YOLOv8n": (8, -4), "YOLOv5s": (8, -10), "YOLOv8s": (8, -2), "v5 (deployed)": (8, 9),
                "Faster R-CNN": (-8, -14)},
        "cpu": {"YOLOv8n": (8, -4), "YOLOv5s": (-8, -14), "YOLOv8s": (-10, -10), "v5 (deployed)": (-10, 10),
                "Faster R-CNN": (-8, -14)}}
fig, ejes = plt.subplots(1, 2, figsize=(ANCHO, 3.6), sharey=True)
for ax, (clave, titulo) in zip(ejes, [("gpu", "(A) GPU (NVIDIA RTX 2070)"),
                                      ("cpu", "(B) CPU (6-core Intel i7-10750H)")]):
    for nombre, grupo, m, gpu, cpu in MODELOS:
        xv = gpu if clave == "gpu" else cpu
        e = ESTILO[grupo]
        ax.scatter(xv, m, s=50, color=e["color"], marker=e["marker"], edgecolor="white", linewidth=1.2, zorder=3)
        dx, dy = ETIQ[clave][nombre]
        ax.annotate(nombre, (xv, m), xytext=(dx, dy), textcoords="offset points", fontsize=8.5, color=TINTA,
                    ha="left" if dx > 0 else "right", va="center")
    if clave == "cpu":
        ax.set_xscale("log")
        ax.axvline(200, color=TINTA2, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.text(230, 0.808, "200 ms = 5 frames/s\nfor one camera", fontsize=8, color=TINTA2, va="center")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.set_xlim(25, 3500)
    else:
        ax.set_xlim(0, 85)
    ax.set_title(titulo, loc="left", color=TINTA)
    ax.set_xlabel("Median latency per image (ms)" + (", log scale" if clave == "cpu" else ""))
    ax.grid(color=REJILLA, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    limpiar(ax)
ejes[0].set_ylabel("mAP@0.5 (external test set)")
ejes[0].set_ylim(0.78, 0.885)
man = [plt.Line2D([], [], ls="", marker=e["marker"], color=e["color"], markeredgecolor="white", markersize=7,
                  label=e["label"]) for e in ESTILO.values()]
fig.legend(handles=man, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.08, 1, 1))
guardar(fig, "Figura_12")
print("ok")
