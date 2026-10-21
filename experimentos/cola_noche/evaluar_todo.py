"""Evalua todos los modelos con un unico protocolo (conf=0.001, iou=0.5).

Medida principal: test externo SIN las 194 imagenes que son copias exactas de
train/val de Zenodo (verificar_duplicados.py) ni las 24 no verificadas. Los
modelos que entrenaron con Zenodo ya "vieron" esas 194; incluirlas infla sus
metricas. Se reporta tambien el test completo como referencia.

Degradaciones: blur y oclusion se parecen a los aumentos de entrenamiento de
v5; desenfoque y baja_luz NO se usaron al entrenar ningun modelo y miden si la
mejora generaliza."""
import json
import os

from ultralytics import YOLO

MODELOS = {
    "v3_anterior": "/v3/best.pt",
    "v4_produccion": "/modelo/best.pt",
    "yolov8n_coco": "/salida/yolov8n_coco/weights/best.pt",
    "yolov8s_coco": "/salida/yolov8s_coco/weights/best.pt",
    "v5_aumentado": "/salida/modelo_v5/weights/best.pt",
}
CONJUNTOS = {"test_completo_con_duplicados": "/ext/eval_dataset/data.yaml"}
for c in ("limpio", "compresion", "blur", "oclusion", "desenfoque", "baja_luz"):
    CONJUNTOS[c] = f"/ext/sin_duplicados/{c}/data.yaml"

# Los data.yaml del test completo apuntan a /data/..., pero en este contenedor
# /data es el volumen del dataset propio; el test externo esta en /ext.
for nombre_c, yaml in list(CONJUNTOS.items()):
    tmp = f"/tmp/{nombre_c}.yaml"
    with open(yaml) as f:
        texto = f.read().replace("path: /data/", "path: /ext/")
    with open(tmp, "w") as f:
        f.write(texto)
    CONJUNTOS[nombre_c] = tmp

resultados = {}
for nombre_m, ruta in MODELOS.items():
    if not os.path.exists(ruta):
        print(f"{nombre_m}: no existe {ruta}, se omite", flush=True)
        continue
    m = YOLO(ruta)
    resultados[nombre_m] = {}
    for nombre_c, yaml in CONJUNTOS.items():
        met = m.val(data=yaml, split="test", conf=0.001, iou=0.5,
                    plots=False, verbose=False, batch=8, workers=2)
        resultados[nombre_m][nombre_c] = {
            "precision": round(float(met.box.mp), 4),
            "recall": round(float(met.box.mr), 4),
            "mAP50": round(float(met.box.map50), 4),
            "mAP50_95": round(float(met.box.map), 4),
            "recall_por_clase": {
                m.names[i]: round(float(met.box.r[i]), 4) for i in m.names
            },
        }
        print(nombre_m, nombre_c, resultados[nombre_m][nombre_c], flush=True)

with open("/salida/evaluacion_final.json", "w") as f:
    json.dump(resultados, f, indent=2)
print("Guardado /salida/evaluacion_final.json")
