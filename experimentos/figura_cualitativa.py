"""Comparacion cualitativa de v5 (YOLOv8s desplegado), YOLOv5s y Faster R-CNN
sobre las mismas imagenes del test externo sin duplicados.

Paso 1 (--predecir): corre los tres modelos (conf >= 0.5) en el test limpio y en
baja luz y guarda las cajas en /salida/predicciones_cualitativas.json.
Paso 2 (--candidatos): clasifica las imagenes por acuerdo entre modelos y dibuja
hojas de contacto para elegir los ejemplos.
Paso 3 (--figura a,b,c,d): dibuja la figura con las imagenes elegidas.
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
import torch

SALIDA = "/salida"
CONJUNTOS = {"limpio": "/ext/sin_duplicados/limpio", "baja_luz": "/ext/sin_duplicados/baja_luz"}
CONF = 0.5
NOMBRES = {"v5": "v5 (YOLOv8s, deployed)", "yolov5s": "YOLOv5s", "frcnn": "Faster R-CNN"}
CLASES = {0: "firearm", 1: "bladed"}


def etiquetas(ruta_img, w, h):
    base = os.path.splitext(ruta_img.replace("/images/", "/labels/"))[0] + ".txt"
    cajas = []
    if os.path.exists(base):
        for l in open(base).read().split("\n"):
            p = l.split()
            if len(p) == 5:
                c, cx, cy, bw, bh = int(p[0]), *map(float, p[1:])
                cajas.append([c, (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h])
    return cajas


def predecir():
    sys.path.insert(0, "/eval/faster_rcnn")
    from entrenar_faster_rcnn import modelo_nuevo
    from ultralytics import YOLO
    import yolov5

    v5 = YOLO("/pesos/v5.pt")
    y5 = yolov5.load("/pesos/v5s.pt", device="cuda:0")
    y5.conf, y5.iou = CONF, 0.5
    fr = modelo_nuevo()
    fr.load_state_dict(torch.load("/pesos/frcnn.pt", map_location="cpu"))
    fr.roi_heads.score_thresh, fr.roi_heads.nms_thresh = CONF, 0.5
    fr.eval().cuda()

    res = {}
    for nombre_c, carpeta in CONJUNTOS.items():
        for ruta in sorted(glob.glob(f"{carpeta}/images/test/*")):
            img = cv2.imread(ruta)
            if img is None:
                continue
            h, w = img.shape[:2]
            clave = f"{nombre_c}/{os.path.basename(ruta)}"
            r = {"gt": etiquetas(ruta, w, h)}
            b = v5.predict(img, imgsz=640, conf=CONF, iou=0.5, verbose=False, device=0)[0].boxes
            r["v5"] = [[int(c), *map(float, xy), float(s)] for c, xy, s in zip(b.cls, b.xyxy, b.conf)]
            p = y5(img[..., ::-1].copy(), size=640).xyxy[0].cpu().numpy()
            r["yolov5s"] = [[int(q[5]), *map(float, q[:4]), float(q[4])] for q in p]
            with torch.no_grad():
                t = torch.from_numpy(img[..., ::-1].copy()).permute(2, 0, 1).float().div(255).cuda()
                o = fr([t])[0]
            r["frcnn"] = [[int(c) - 1, *map(float, xy), float(s)] for c, xy, s in
                          zip(o["labels"].cpu(), o["boxes"].cpu(), o["scores"].cpu())]
            res[clave] = r
        print(nombre_c, "listo", flush=True)
    json.dump(res, open(f"{SALIDA}/predicciones_cualitativas.json", "w"))


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def evaluar(gt, pred):
    """(aciertos, fallos, falsas alarmas) con IoU >= 0.5 y misma clase."""
    usados, aciertos = set(), 0
    for g in gt:
        for k, p in enumerate(pred):
            if k not in usados and p[0] == g[0] and iou(g[1:5], p[1:5]) >= 0.5:
                usados.add(k)
                aciertos += 1
                break
    return aciertos, len(gt) - aciertos, len(pred) - len(usados)


def candidatos():
    res = json.load(open(f"{SALIDA}/predicciones_cualitativas.json"))
    grupos = {"todos_aciertan": [], "solo_v5": [], "solo_frcnn": [], "v5_y_frcnn_no_yolov5": [],
              "baja_luz_difieren": [], "falsa_alarma_sin_arma": []}
    for clave, r in res.items():
        ev = {m: evaluar(r["gt"], r[m]) for m in NOMBRES}
        ok = {m: ev[m][1] == 0 and ev[m][2] == 0 and len(r["gt"]) > 0 for m in NOMBRES}
        luz = clave.startswith("baja_luz")
        if not luz and len(r["gt"]) in (1, 2) and all(ok.values()):
            grupos["todos_aciertan"].append(clave)
        if not luz and ok["v5"] and not ok["yolov5s"] and not ok["frcnn"]:
            grupos["solo_v5"].append(clave)
        if not luz and ok["frcnn"] and not ok["v5"] and not ok["yolov5s"]:
            grupos["solo_frcnn"].append(clave)
        if not luz and ok["v5"] and ok["frcnn"] and not ok["yolov5s"]:
            grupos["v5_y_frcnn_no_yolov5"].append(clave)
        if luz and len(set(ok.values())) == 2:
            grupos["baja_luz_difieren"].append(clave)
        if not luz and not r["gt"] and any(ev[m][2] > 0 for m in NOMBRES):
            grupos["falsa_alarma_sin_arma"].append(clave)
    for g, lista in grupos.items():
        print(g, len(lista))
        filas = [fila(res, c) for c in lista[:12]]
        if filas:
            cv2.imwrite(f"{SALIDA}/candidatos_{g}.jpg", np.vstack(filas))
    json.dump(grupos, open(f"{SALIDA}/candidatos.json", "w"), indent=1)


COLORES = {"gt": (255, 255, 255), "v5": (52, 104, 235), "yolov5s": (214, 120, 42), "frcnn": (122, 175, 27)}


def dibujar(img, cajas, color, gt=False):
    for c in cajas:
        x1, y1, x2, y2 = map(int, c[1:5])
        if gt:
            # Anotacion real: trazo punteado blanco con borde negro, visible sobre cualquier fondo.
            for grosor, col in ((5, (0, 0, 0)), (2, color)):
                for k in range(x1, x2, 12):
                    cv2.line(img, (k, y1), (min(k + 6, x2), y1), col, grosor)
                    cv2.line(img, (k, y2), (min(k + 6, x2), y2), col, grosor)
                for k in range(y1, y2, 12):
                    cv2.line(img, (x1, k), (x1, min(k + 6, y2)), col, grosor)
                    cv2.line(img, (x2, k), (x2, min(k + 6, y2)), col, grosor)
        else:
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
            txt = f"{CLASES.get(c[0], c[0])} {c[5]:.2f}"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            ya = max(th + 4, y1)
            cv2.rectangle(img, (x1, ya - th - 4), (x1 + tw + 4, ya), color, -1)
            cv2.putText(img, txt, (x1 + 2, ya - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def panel(clave, r, modelo, lado=420, alto=None):
    nombre_c, archivo = clave.split("/", 1)
    img = cv2.imread(f"{CONJUNTOS[nombre_c]}/images/test/{archivo}")
    dibujar(img, r["gt"], COLORES["gt"], gt=True)
    dibujar(img, r[modelo], COLORES[modelo])
    h, w = img.shape[:2]
    alto = alto or lado
    e = min(lado / w, alto / h)
    img = cv2.resize(img, (int(w * e), int(h * e)))
    lienzo = np.full((alto, lado, 3), 255, np.uint8)
    y0, x0 = (alto - img.shape[0]) // 2, (lado - img.shape[1]) // 2
    lienzo[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
    return lienzo


def fila(res, clave):
    r = res[clave]
    paneles = [panel(clave, r, m, 300) for m in NOMBRES]
    cv2.putText(paneles[0], clave[:40], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    return np.hstack(paneles)


def figura(claves):
    res = json.load(open(f"{SALIDA}/predicciones_cualitativas.json"))
    sep = np.full((236, 6, 3), 255, np.uint8)
    filas = []
    for c in claves:
        p = [panel(c, res[c], m, 420, 236) for m in NOMBRES]
        filas.append(np.hstack([p[0], sep, p[1], sep, p[2]]))
        filas.append(np.full((10, filas[-1].shape[1], 3), 255, np.uint8))
    cv2.imwrite(f"{SALIDA}/figura_cualitativa_paneles.png", np.vstack(filas))
    json.dump({"claves": claves}, open(f"{SALIDA}/figura_cualitativa_claves.json", "w"))


if __name__ == "__main__":
    if "--predecir" in sys.argv:
        predecir()
    if "--candidatos" in sys.argv:
        candidatos()
    if "--figura" in sys.argv:
        figura(sys.argv[sys.argv.index("--figura") + 1].split(","))


def componer():
    """Agrega titulos de columna, descripcion de cada fila y leyenda (se corre en el host)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    paneles = plt.imread("docs/evidencia_externa/comparacion/figura_cualitativa_paneles.png")
    filas = ["(a) CCTV-like scene:\nall three detect\nthe knife",
             "(b) Two knives:\nYOLOv5s misses one",
             "(c) Low light, sporting\nrifle: only Faster R-CNN\ndetects it",
             "(d) No weapon:\nYOLOv5s and Faster\nR-CNN raise false alarms"]
    colores = {"v5": "#eb6834", "yolov5s": "#2a78d6", "frcnn": "#1baf7a"}
    fig = plt.figure(figsize=(7.4, 5.6), dpi=300)
    ax = fig.add_axes([0.2, 0.08, 0.79, 0.86])
    ax.imshow(paneles)
    ax.axis("off")
    alto, ancho = paneles.shape[:2]
    for k, (m, nombre) in enumerate(NOMBRES.items()):
        ax.text((k + 0.5) * ancho / 3, -12, nombre, ha="center", va="bottom", fontsize=9, color=colores[m],
                fontweight="bold")
    for k, t in enumerate(filas):
        ax.text(-14, (k + 0.5) * alto / 4, t, ha="right", va="center", fontsize=8, color="#0b0b0b")
    leyenda = [Line2D([], [], color="#555555", ls=(0, (2, 2)), lw=1.5, label="Annotated weapon"),
               Line2D([], [], color="#0b0b0b", lw=2, label="Detection: class and confidence (threshold 0.5)")]
    fig.legend(handles=leyenda, loc="lower center", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.58, 0.0))
    fig.savefig("docs/evidencia_externa/comparacion/comparacion_cualitativa.png", facecolor="white")


if __name__ == "__main__" and "--componer" in sys.argv:
    componer()
