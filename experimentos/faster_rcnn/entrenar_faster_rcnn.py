"""Faster R-CNN como segundo detector de referencia (Reviewer 1, punto 2:
"comparing YOLOv8n to at least one alternative (e.g., YOLOv5, Faster R-CNN)").

Mismas condiciones que la comparacion YOLO (entrenar_coco.py): pesos COCO,
mismo dataset combinado (data_combinado.yaml: dataset propio + train de
Zenodo), lado mayor 640 px, semilla 0. Modelo: torchvision
fasterrcnn_resnet50_fpn_v2 (backbone ResNet-50 + FPN, la referencia de dos
etapas habitual). Aumento: solo volteo horizontal, el estandar de Faster
R-CNN; YOLO usa ademas mosaico y HSV, diferencia que se declara.

Guarda un checkpoint por epoca y retoma solo si se corta (la VM de Docker ya
se quedo sin memoria una vez en la cola nocturna).

Uso: python entrenar_faster_rcnn.py <epocas> [--prueba N_iteraciones]
"""
import glob
import json
import math
import os
import random
import sys
import time

import cv2
import numpy as np
import torch
from torchvision.models.detection import (FasterRCNN_ResNet50_FPN_V2_Weights,
                                          fasterrcnn_resnet50_fpn_v2)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

DIRS_TRAIN = ["/data/dataset_80_20/train/images", "/zenodo/images/train"]
SALIDA = "/salida/faster_rcnn"
LOTE, WORKERS, LR_BASE = 4, 4, 0.01
os.makedirs(SALIDA, exist_ok=True)


def log(*a):
    linea = time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a)
    print(linea, flush=True)
    with open(f"{SALIDA}/progreso.log", "a") as f:
        f.write(linea + "\n")


def ruta_etiqueta(img):
    base = os.path.splitext(img.replace("/images/", "/labels/"))[0]
    return base + ".txt"


class DatasetYolo(torch.utils.data.Dataset):
    """Lee imagenes y etiquetas en formato YOLO (clase cx cy w h, normalizado).
    Clases YOLO 0/1 pasan a 1/2: en torchvision la 0 es el fondo."""

    def __init__(self, dirs, voltear):
        self.imgs = sorted(p for d in dirs for p in glob.glob(f"{d}/*")
                           if p.lower().endswith((".jpg", ".jpeg", ".png")))
        self.voltear = voltear

    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, i):
        img = cv2.imread(self.imgs[i])[..., ::-1]
        h, w = img.shape[:2]
        cajas, clases = [], []
        et = ruta_etiqueta(self.imgs[i])
        if os.path.exists(et):
            for linea in open(et).read().split("\n"):
                p = linea.split()
                if len(p) != 5:
                    continue
                c, cx, cy, bw, bh = int(p[0]), *map(float, p[1:])
                x1, y1 = (cx - bw / 2) * w, (cy - bh / 2) * h
                x2, y2 = (cx + bw / 2) * w, (cy + bh / 2) * h
                if x2 - x1 >= 1 and y2 - y1 >= 1:
                    cajas.append([x1, y1, x2, y2])
                    clases.append(c + 1)
        cajas = torch.tensor(cajas, dtype=torch.float32).reshape(-1, 4)
        if self.voltear and random.random() < 0.5:
            img = img[:, ::-1]
            cajas[:, [0, 2]] = w - cajas[:, [2, 0]]
        t = torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1).float() / 255
        return t, {"boxes": cajas, "labels": torch.tensor(clases, dtype=torch.int64)}


def modelo_nuevo():
    m = fasterrcnn_resnet50_fpn_v2(weights=FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1,
                                   min_size=640, max_size=640)
    m.roi_heads.box_predictor = FastRCNNPredictor(
        m.roi_heads.box_predictor.cls_score.in_features, 3)
    return m


def main():
    epocas = int(sys.argv[1])
    prueba = int(sys.argv[sys.argv.index("--prueba") + 1]) if "--prueba" in sys.argv else 0
    random.seed(0); np.random.seed(0); torch.manual_seed(0)

    ds = DatasetYolo(DIRS_TRAIN, voltear=True)
    dl = torch.utils.data.DataLoader(ds, batch_size=LOTE, shuffle=True, num_workers=WORKERS,
                                     collate_fn=lambda b: tuple(zip(*b)), drop_last=True,
                                     generator=torch.Generator().manual_seed(0))
    m = modelo_nuevo().cuda()
    params = [p for p in m.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=LR_BASE, momentum=0.9, weight_decay=1e-4)
    total = epocas * len(dl)
    calentamiento = 1000

    def lr_en(it):  # calentamiento lineal y luego coseno, como el lr de YOLO
        if it < calentamiento:
            return LR_BASE * (0.001 + 0.999 * it / calentamiento)
        return LR_BASE * (0.01 + 0.99 * 0.5 * (1 + math.cos(math.pi * it / total)))

    escalador = torch.amp.GradScaler()
    inicio = 0
    ck = f"{SALIDA}/ultimo.pt"
    if os.path.exists(ck) and not prueba:
        estado = torch.load(ck, map_location="cuda", weights_only=False)
        m.load_state_dict(estado["modelo"]); opt.load_state_dict(estado["opt"])
        escalador.load_state_dict(estado["escalador"]); inicio = estado["epoca"] + 1
        log(f"retomando desde la epoca {inicio + 1}")
    log(f"imagenes={len(ds)} lote={LOTE} iteraciones/epoca={len(dl)} epocas={epocas}")

    for ep in range(inicio, epocas):
        m.train()
        t0, suma = time.time(), 0.0
        for i, (imgs, objs) in enumerate(dl):
            it = ep * len(dl) + i
            for g in opt.param_groups:
                g["lr"] = lr_en(it)
            imgs = [x.cuda(non_blocking=True) for x in imgs]
            objs = [{k: v.cuda() for k, v in o.items()} for o in objs]
            with torch.autocast("cuda", dtype=torch.float16):
                perdidas = m(imgs, objs)
                perdida = sum(perdidas.values())
            opt.zero_grad(set_to_none=True)
            escalador.scale(perdida).backward()
            escalador.step(opt); escalador.update()
            suma += perdida.item()
            if i % 200 == 0 or (prueba and i % 20 == 0):
                vel = (i + 1) / (time.time() - t0)
                log(f"epoca {ep + 1}/{epocas} it {i}/{len(dl)} perdida {perdida.item():.3f} "
                    f"lr {lr_en(it):.5f} {vel:.2f} it/s, quedan {(len(dl) - i) / vel / 60:.0f} min de epoca")
            if prueba and i + 1 >= prueba:
                log(f"PRUEBA: {vel:.2f} it/s, epoca completa ~{len(dl) / vel / 3600:.2f} h, "
                    f"memoria GPU max {torch.cuda.max_memory_allocated() / 2**30:.1f} GB")
                return
        torch.save({"modelo": m.state_dict(), "opt": opt.state_dict(),
                    "escalador": escalador.state_dict(), "epoca": ep}, ck + ".tmp")
        os.replace(ck + ".tmp", ck)
        log(f"epoca {ep + 1}/{epocas} completa, perdida media {suma / len(dl):.4f}, "
            f"{(time.time() - t0) / 60:.1f} min")

    torch.save(m.state_dict(), f"{SALIDA}/final.pt")
    json.dump({"epocas": epocas, "lote": LOTE, "lr_base": LR_BASE, "imagenes": len(ds),
               "torch": torch.__version__}, open(f"{SALIDA}/config.json", "w"), indent=2)
    log("FIN entrenamiento")


if __name__ == "__main__":
    main()
