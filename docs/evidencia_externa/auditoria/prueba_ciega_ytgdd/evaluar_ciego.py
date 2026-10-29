import json
from ultralytics import YOLO
m = YOLO("/modelo/best.pt")
met = m.val(data="/ciego/ytgdd_test/data.yaml", split="test", conf=0.001, iou=0.5, batch=8, workers=2,
            imgsz=640, plots=True, project="/ciego/salida", name="v5", exist_ok=True, verbose=False)
i = list(met.box.ap_class_index).index(0)
res = {"arma_fuego": {"precision": float(met.box.p[i]), "recall": float(met.box.r[i]),
                      "AP50": float(met.box.ap50[i]), "AP50_95": float(met.box.ap[i])}}
# nivel imagen al umbral de operacion 0.65
import glob, os
imgs = sorted(glob.glob("/ciego/ytgdd_test/images/test/*.jpg"))
con_arma = alerta = alerta_blanca_solo = 0
for k in range(0, len(imgs), 16):
    for r in m(imgs[k:k + 16], conf=0.65, verbose=False):
        lab = "/ciego/ytgdd_test/labels/test/" + os.path.basename(r.path)[:-4] + ".txt"
        if os.path.getsize(lab) == 0:
            continue
        con_arma += 1
        clases = [int(c) for c in r.boxes.cls.tolist()]
        if clases:
            alerta += 1
            if 0 not in clases:
                alerta_blanca_solo += 1
res["nivel_imagen_umbral_065"] = {"imagenes_con_arma": con_arma, "con_alerta": alerta,
                                  "tasa_alerta": alerta / con_arma,
                                  "alerta_solo_como_arma_blanca": alerta_blanca_solo}
print(json.dumps(res, indent=2))
json.dump(res, open("/ciego/resultado_ciego.json", "w"), indent=2)
