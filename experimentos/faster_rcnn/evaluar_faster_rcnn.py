"""Evalua Faster R-CNN y los modelos YOLO con UN MISMO evaluador, sobre el
test externo sin duplicados y sus degradaciones, y mide su latencia por imagen.

Ultralytics y torchvision no comparten evaluador, asi que aqui se reimplementa
el de Ultralytics (ap_per_class: emparejamiento por IoU, AP con interpolacion
de 101 puntos, P y R en la confianza de F1 maximo) y se aplica a las
predicciones de todos los modelos (conf >= 0.001, hasta 300 cajas, NMS IoU
0.5). Los modelos YOLO sirven de control: sus cifras deben coincidir con las
de m.val() en evaluacion_final.json.

Uso: python evaluar_faster_rcnn.py [--solo-control] [--sin-latencia]
"""
import glob
import json
import os
import sys
import time

import cv2
import numpy as np
import torch
from torchvision.ops import box_iou

sys.path.insert(0, os.path.dirname(__file__))
from entrenar_faster_rcnn import modelo_nuevo, ruta_etiqueta  # noqa: E402

CONJUNTOS = ["limpio", "compresion", "blur", "oclusion", "desenfoque", "baja_luz", "elevada", "lateral"]
IOUS = torch.linspace(0.5, 0.95, 10)
YOLOS = {"yolov8s_coco": "/salida_noche/yolov8s_coco/weights/best.pt",
         "v5_desplegado": "/salida_noche/modelo_v5/weights/best.pt"}
FRCNN = "/salida/faster_rcnn/final.pt"


def etiquetas(img_path, w, h):
    cajas, clases = [], []
    et = ruta_etiqueta(img_path)
    if os.path.exists(et):
        for linea in open(et).read().split("\n"):
            p = linea.split()
            if len(p) == 5:
                c, cx, cy, bw, bh = int(p[0]), *map(float, p[1:])
                cajas.append([(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h])
                clases.append(c)
    return torch.tensor(cajas).reshape(-1, 4), torch.tensor(clases)


def emparejar(pred_cls, gt_cls, iou):
    """Igual que DetectionValidator.match_predictions de Ultralytics."""
    correcto = np.zeros((len(pred_cls), len(IOUS)), dtype=bool)
    iou = (iou * (gt_cls[:, None] == pred_cls[None, :])).numpy()
    for i, t in enumerate(IOUS.tolist()):
        m = np.array(np.nonzero(iou >= t)).T
        if m.shape[0]:
            if m.shape[0] > 1:
                m = m[iou[m[:, 0], m[:, 1]].argsort()[::-1]]
                m = m[np.unique(m[:, 1], return_index=True)[1]]
                m = m[np.unique(m[:, 0], return_index=True)[1]]
            correcto[m[:, 1].astype(int), i] = True
    return correcto


def ap_101(r, p):
    mrec = np.concatenate(([0.0], r, [1.0]))
    mpre = np.flip(np.maximum.accumulate(np.flip(np.concatenate(([1.0], p, [0.0])))))
    x = np.linspace(0, 1, 101)
    return np.trapz(np.interp(x, mrec, mpre), x)


def metricas(tp, conf, pcls, gcls, nc=2):
    """Igual que ultralytics.utils.metrics.ap_per_class."""
    orden = np.argsort(-conf)
    tp, conf, pcls = tp[orden], conf[orden], pcls[orden]
    px = np.linspace(0, 1, 1000)
    ap = np.zeros((nc, tp.shape[1])); p_c = np.zeros((nc, 1000)); r_c = np.zeros((nc, 1000))
    for c in range(nc):
        i = pcls == c
        n_l, n_p = (gcls == c).sum(), i.sum()
        if n_p == 0 or n_l == 0:
            continue
        fpc, tpc = (1 - tp[i]).cumsum(0), tp[i].cumsum(0)
        rec = tpc / (n_l + 1e-16)
        pre = tpc / (tpc + fpc)
        r_c[c] = np.interp(-px, -conf[i], rec[:, 0], left=0)
        p_c[c] = np.interp(-px, -conf[i], pre[:, 0], left=1)
        for j in range(tp.shape[1]):
            ap[c, j] = ap_101(rec[:, j], pre[:, j])
    f1 = 2 * p_c * r_c / (p_c + r_c + 1e-16)
    k = int(np.convolve(f1.mean(0), np.ones(int(round(1000 * 0.1 * 2)) // 2 * 2 + 1) /
                        (int(round(1000 * 0.1 * 2)) // 2 * 2 + 1), mode="same").argmax())
    return {"precision": round(float(p_c[:, k].mean()), 4), "recall": round(float(r_c[:, k].mean()), 4),
            "mAP50": round(float(ap[:, 0].mean()), 4), "mAP50_95": round(float(ap.mean()), 4),
            "recall_por_clase": {"arma_fuego": round(float(r_c[0, k]), 4),
                                 "arma_blanca": round(float(r_c[1, k]), 4)},
            "mAP50_por_clase": {"arma_fuego": round(float(ap[0, 0]), 4),
                                "arma_blanca": round(float(ap[1, 0]), 4)}}


def predictor(nombre, disp, conf):
    """Devuelve f(img_bgr) -> (cajas xyxy, confianzas, clases 0/1)."""
    if nombre == "faster_rcnn":
        m = modelo_nuevo()
        m.load_state_dict(torch.load(FRCNN, map_location="cpu"))
        m.roi_heads.score_thresh, m.roi_heads.nms_thresh = conf, 0.5
        m.roi_heads.detections_per_img = 300
        m.eval().to(disp)

        @torch.no_grad()
        def f(img):
            t = torch.from_numpy(img[..., ::-1].copy()).permute(2, 0, 1).float().div(255).to(disp)
            o = m([t])[0]
            return o["boxes"].cpu(), o["scores"].cpu(), (o["labels"] - 1).cpu()
        return f
    from ultralytics import YOLO
    m = YOLO(YOLOS[nombre])

    def f(img):
        b = m.predict(img, imgsz=640, conf=conf, iou=0.5, max_det=300, device=disp, verbose=False)[0].boxes
        return b.xyxy.cpu(), b.conf.cpu(), b.cls.cpu().long()
    return f


def evaluar(f, conjunto):
    tps, confs, pcls, gcls = [], [], [], []
    for ruta in sorted(glob.glob(f"/ext/sin_duplicados/{conjunto}/images/test/*")):
        img = cv2.imread(ruta)
        h, w = img.shape[:2]
        gb, gc = etiquetas(ruta, w, h)
        pb, pc, pk = f(img)
        gcls.append(gc.numpy())
        if len(pb) == 0:
            continue
        if len(gb):
            tps.append(emparejar(pk, gc, box_iou(gb, pb.float())))
        else:
            tps.append(np.zeros((len(pb), len(IOUS)), dtype=bool))
        confs.append(pc.numpy()); pcls.append(pk.numpy())
    return metricas(np.concatenate(tps), np.concatenate(confs), np.concatenate(pcls), np.concatenate(gcls))


def latencia(f, disp):
    imgs = [cv2.imread(r) for r in sorted(glob.glob("/ext/sin_duplicados/limpio/images/test/*.jpg"))[:220]]
    t = []
    for i, img in enumerate(imgs):
        if disp != "cpu":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        f(img)
        if disp != "cpu":
            torch.cuda.synchronize()
        if i >= 20:
            t.append((time.perf_counter() - t0) * 1000)
    return {"P50_ms": round(float(np.percentile(t, 50)), 1), "P95_ms": round(float(np.percentile(t, 95)), 1)}


def main():
    solo_control = "--solo-control" in sys.argv
    modelos = list(YOLOS) if solo_control else ["faster_rcnn", *YOLOS]
    conjuntos = ["limpio"] if solo_control else CONJUNTOS
    res = {}
    for nombre in modelos:
        f = predictor(nombre, "cuda:0", 0.001)
        res[nombre] = {c: evaluar(f, c) for c in conjuntos}
        for c in conjuntos:
            print(nombre, c, res[nombre][c], flush=True)
        if "--sin-latencia" not in sys.argv:
            res[nombre]["latencia"] = {d: latencia(predictor(nombre, d, 0.25), d) for d in ("cuda:0", "cpu")}
            print(nombre, "latencia", res[nombre]["latencia"], flush=True)
    res["_entorno"] = {"torch": torch.__version__, "gpu": torch.cuda.get_device_name(0),
                       "hilos_cpu_torch": torch.get_num_threads()}
    salida = "/salida/evaluacion_control.json" if solo_control else "/salida/evaluacion_faster_rcnn.json"
    json.dump(res, open(salida, "w"), indent=2)
    print("Guardado", salida)


if __name__ == "__main__":
    main()
