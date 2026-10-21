"""Evaluacion completa en el conjunto externo (Reviewer 1, punto 1):
precision/recall por clase, matriz de confusion, y casos de fallo
representativos (falsos negativos y falsos positivos reales, con imagen).
"""
import json
import os
import cv2
from ultralytics import YOLO

MODELO = "/modelo/best.pt"
DATA_YAML = "/data/eval_dataset/data.yaml"
IMAGES_DIR = "/data/eval_dataset/images/test"
LABELS_DIR = "/data/eval_dataset/labels/test"
SALIDA = "/data/eval_dataset/fallos"
os.makedirs(SALIDA, exist_ok=True)

m = YOLO(MODELO)
CLASES = m.names  # {0: 'arma_fuego', 1: 'arma_blanca'}

# --- 1) Metricas por clase + matriz de confusion (via ultralytics val) ---
met = m.val(data=DATA_YAML, split="test", conf=0.25, iou=0.5,
            plots=True, project="/data/eval_dataset", name="val_completo", exist_ok=True)

por_clase = {}
for i, nombre in CLASES.items():
    por_clase[nombre] = {
        "precision": float(met.box.p[i]),
        "recall": float(met.box.r[i]),
        "mAP50": float(met.box.ap50[i]),
        "mAP50_95": float(met.box.ap[i]),
    }

resumen = {
    "global": {
        "precision": float(met.box.mp),
        "recall": float(met.box.mr),
        "mAP50": float(met.box.map50),
        "mAP50_95": float(met.box.map),
    },
    "por_clase": por_clase,
}

print("=" * 60)
print("PRECISION / RECALL POR CLASE")
print("=" * 60)
print(json.dumps(resumen, indent=2, ensure_ascii=False))

with open("/data/eval_dataset/metricas_por_clase.json", "w") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)


# --- 2) Casos de fallo representativos ---
def cajas_reales(txt_path):
    cajas = []
    if not os.path.exists(txt_path):
        return cajas
    for linea in open(txt_path):
        p = linea.split()
        if len(p) < 5:
            continue
        cid, cx, cy, w, h = int(p[0]), float(p[1]), float(p[2]), float(p[3]), float(p[4])
        cajas.append((cid, cx, cy, w, h))
    return cajas


def iou_norm(a, b):
    ax1, ay1, ax2, ay2 = a[1] - a[3] / 2, a[2] - a[4] / 2, a[1] + a[3] / 2, a[2] + a[4] / 2
    bx1, by1, bx2, by2 = b[1] - b[3] / 2, b[2] - b[4] / 2, b[1] + b[3] / 2, b[2] + b[4] / 2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    area_a = a[3] * a[4]
    area_b = b[3] * b[4]
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


falsos_negativos = []  # arma real que el modelo no detecto
falsos_positivos = []  # el modelo detecto algo que no hay, o clase equivocada

archivos = sorted(os.listdir(IMAGES_DIR))
for nombre_img in archivos:
    ruta_img = os.path.join(IMAGES_DIR, nombre_img)
    base = os.path.splitext(nombre_img)[0]
    ruta_txt = os.path.join(LABELS_DIR, base + ".txt")
    reales = cajas_reales(ruta_txt)

    r = m(ruta_img, conf=0.25, verbose=False)[0]
    predichas = []
    for b in r.boxes:
        cid = int(b.cls[0])
        xc, yc, w, h = b.xywhn[0].tolist()
        predichas.append((cid, xc, yc, w, h))

    emparejadas_reales = set()
    emparejadas_pred = set()
    for i, real in enumerate(reales):
        for j, pred in enumerate(predichas):
            if j in emparejadas_pred:
                continue
            if iou_norm(real, pred) >= 0.5 and real[0] == pred[0]:
                emparejadas_reales.add(i)
                emparejadas_pred.add(j)
                break

    for i, real in enumerate(reales):
        if i not in emparejadas_reales and len(falsos_negativos) < 6:
            falsos_negativos.append((nombre_img, ruta_img, real))

    for j, pred in enumerate(predichas):
        if j not in emparejadas_pred and len(falsos_positivos) < 6:
            falsos_positivos.append((nombre_img, ruta_img, pred))

    if len(falsos_negativos) >= 6 and len(falsos_positivos) >= 6:
        break

print()
print(f"Falsos negativos encontrados: {len(falsos_negativos)}")
print(f"Falsos positivos encontrados: {len(falsos_positivos)}")


def guardar_caso(nombre_archivo, ruta_img, caja, etiqueta, carpeta):
    img = cv2.imread(ruta_img)
    h, w = img.shape[:2]
    cid, cx, cy, bw, bh = caja
    x1, y1 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
    x2, y2 = int((cx + bw / 2) * w), int((cy + bh / 2) * h)
    color = (0, 0, 255) if etiqueta == "FN" else (0, 165, 255)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(img, f"{etiqueta}:{CLASES[cid]}", (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    out = os.path.join(carpeta, f"{etiqueta}_{nombre_archivo}")
    cv2.imwrite(out, img)
    return out


for nombre_archivo, ruta_img, caja in falsos_negativos:
    guardar_caso(nombre_archivo, ruta_img, caja, "FN", SALIDA)

for nombre_archivo, ruta_img, caja in falsos_positivos:
    guardar_caso(nombre_archivo, ruta_img, caja, "FP", SALIDA)

print(f"Casos guardados en {SALIDA}")
