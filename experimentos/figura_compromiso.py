"""Figura 12 del articulo: precision (mAP@0.5) frente a latencia por imagen, en
GPU y en CPU, para los detectores comparados (Tabla 4). Muestra el compromiso:
Faster R-CNN apenas gana precision y es mucho mas lento.

Uso: python figura_compromiso.py  (desde la raiz del repositorio)
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

# Tabla 4: mAP@0.5 en el test externo sin duplicados; latencia P50 por imagen (ms).
MODELOS = [
    # nombre, grupo, mAP50, GPU P50, CPU P50
    ("YOLOv8n", "yolo", 0.795, 13.6, 53.7),
    ("YOLOv5s", "yolo", 0.838, 17.7, 98.4),
    ("YOLOv8s", "yolo", 0.854, 16.4, 128.7),
    ("v5 (deployed)", "v5", 0.859, 12.9, 119.4),
    ("Faster R-CNN", "frcnn", 0.864, 71.4, 2040.5),
]
# Paleta categorica validada (3 tonos, todos los pares) y forma de marcador
# como segunda codificacion: el color nunca es la unica pista.
ESTILO = {
    "yolo": dict(color="#2a78d6", marker="o", label="YOLO from COCO weights"),
    "v5": dict(color="#eb6834", marker="D", label="Deployed model (YOLOv8s, v5)"),
    "frcnn": dict(color="#1baf7a", marker="s", label="Faster R-CNN (two-stage)"),
}
TINTA, TINTA2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"

# Desplazamiento de cada etiqueta (puntos) para que no se pisen.
ETIQUETAS = {
    "gpu": {"YOLOv8n": (8, -4), "YOLOv5s": (8, -10), "YOLOv8s": (8, -2), "v5 (deployed)": (8, 9),
            "Faster R-CNN": (-8, -14)},
    "cpu": {"YOLOv8n": (8, -4), "YOLOv5s": (-8, -14), "YOLOv8s": (10, -10), "v5 (deployed)": (-6, 11),
            "Faster R-CNN": (-8, -14)},
}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": TINTA2,
                     "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2})
fig, ejes = plt.subplots(1, 2, figsize=(7.4, 3.5), dpi=300, sharey=True)

for ax, (clave, col, titulo) in zip(ejes, [("gpu", 3, "(a) GPU (NVIDIA RTX 2070)"),
                                           ("cpu", 4, "(b) CPU (6-core Intel i7-10750H)")]):
    for nombre, grupo, m, gpu, cpu in MODELOS:
        x = gpu if clave == "gpu" else cpu
        e = ESTILO[grupo]
        ax.scatter(x, m, s=46, color=e["color"], marker=e["marker"], edgecolor="white", linewidth=1.2,
                   zorder=3)
        dx, dy = ETIQUETAS[clave][nombre]
        ax.annotate(nombre, (x, m), xytext=(dx, dy), textcoords="offset points", fontsize=8, color=TINTA,
                    ha="left" if dx > 0 else "right", va="center")
    if clave == "cpu":
        ax.set_xscale("log")
        ax.axvline(200, color=TINTA2, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.text(218, 0.882, "200 ms = 5 frames/s\nfor one camera", fontsize=7.5, color=TINTA2, va="top")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.set_xlim(25, 3500)
    else:
        ax.set_xlim(0, 85)
    ax.set_title(titulo, fontsize=9, color=TINTA, loc="left")
    ax.set_xlabel("Median latency per image (ms)" + (", log scale" if clave == "cpu" else ""))
    ax.grid(color=REJILLA, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)

ejes[0].set_ylabel("mAP@0.5 (external test set)")
ejes[0].set_ylim(0.78, 0.885)
manejadores = [plt.Line2D([], [], ls="", marker=e["marker"], color=e["color"], markeredgecolor="white",
                          markersize=7, label=e["label"]) for e in ESTILO.values()]
fig.legend(handles=manejadores, loc="lower center", ncol=3, frameon=False, fontsize=8,
           bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig("docs/evidencia_externa/comparacion/compromiso_precision_latencia.png", facecolor="white")
print("ok")
