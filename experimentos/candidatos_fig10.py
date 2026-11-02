"""Candidatos para la Figura 10 (errores de v5, conf 0.25) sin marca de agua al pie.
Marca de agua tipo stock: franja inferior casi blanca con texto oscuro."""
import glob, json, os
import cv2, numpy as np
from ultralytics import YOLO
m = YOLO("/modelo/best.pt")
IMG, LAB = "/ext/sin_duplicados/limpio/images/test", "/ext/sin_duplicados/limpio/labels/test"
def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i + 1e-9)
def marca_agua(img):
    h = img.shape[0]; g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    franja = g[int(h*0.93):]
    return franja.mean() > 225 and (franja < 120).mean() > 0.004
res = {}
imgs = sorted(glob.glob(IMG + "/*"))
for k in range(0, len(imgs), 16):
    for r in m(imgs[k:k+16], conf=0.25, iou=0.5, verbose=False):
        img = r.orig_img; h, w = img.shape[:2]
        gts = []
        lab = os.path.join(LAB, os.path.splitext(os.path.basename(r.path))[0] + ".txt")
        if os.path.exists(lab):
            for l in open(lab):
                c, x, y, bw, bh = map(float, l.split())
                gts.append([int(c), [(x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h]])
        preds = sorted(zip(r.boxes.conf.tolist(), r.boxes.cls.int().tolist(), r.boxes.xyxy.tolist()), reverse=True)
        usado, fps = set(), []
        for conf, c, b in preds:
            cand = [(iou(b, g), j) for j, (gc, g) in enumerate(gts) if gc == c and j not in usado]
            best = max(cand, default=(0, -1))
            if best[0] >= 0.5: usado.add(best[1]); continue
            misma = max([iou(b, g) for gc, g in gts if gc == c], default=0)
            fps.append([c, round(conf, 2), b, "desplazada" if 0.1 <= misma < 0.5 else "otra"])
        fns = [g for j, g in enumerate(gts) if j not in usado]
        res[os.path.basename(r.path)] = {"marca_agua": bool(marca_agua(img)), "gt": gts, "fn": fns, "fp": fps,
                                         "w": w, "h": h}
json.dump(res, open("/ext/fp_analisis/errores_por_imagen.json", "w"))
print("imagenes con marca de agua al pie:", sum(v["marca_agua"] for v in res.values()))
def hoja(nombre, claves):
    tiles = []
    for c in claves[:48]:
        img = cv2.imread(f"{IMG}/{c}"); v = res[c]
        for gc, b in v["fn"]: cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 0, 255), 3)
        for pc, conf, b, t in v["fp"]: cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 165, 255), 3)
        t = cv2.resize(img, (300, 225)); cv2.putText(t, c[:22], (4, 18), 0, 0.5, (255, 255, 0), 1); tiles.append(t)
    while len(tiles) % 8: tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(f"/ext/fp_analisis/hoja_{nombre}.jpg", np.vstack([np.hstack(tiles[i:i+8]) for i in range(0, len(tiles), 8)]))
limpias = {k: v for k, v in res.items() if not v["marca_agua"]}
hoja("fn_blanca", [k for k, v in limpias.items() if any(g[0] == 1 for g in v["fn"])])
hoja("fn_fuego", [k for k, v in limpias.items() if any(g[0] == 0 for g in v["fn"])])
hoja("fp_sin_arma", [k for k, v in limpias.items() if any(f[3] == "otra" for f in v["fp"]) and not v["gt"]])
hoja("fp_desplazada", [k for k, v in limpias.items() if any(f[3] == "desplazada" for f in v["fp"])])
print({n: len(x) for n, x in [("limpias", limpias)]})
