"""Entrenamiento desde pesos COCO con el mismo dataset, epocas, batch e imgsz
que YOLOv5s (entrenar_yolov5.sh), para que la comparacion de arquitecturas
sea en igualdad de condiciones de inicializacion (Reviewer 1, punto 2).
Uso: python entrenar_coco.py <pesos_coco> <nombre_salida>
"""
import hashlib
import sys
from ultralytics import YOLO

pesos, nombre = sys.argv[1], sys.argv[2]

YOLO(pesos).train(
    data="/eval/data_combinado.yaml",
    epochs=20,
    imgsz=640,
    batch=16,
    patience=8,
    seed=0,
    project="/salida",
    name=nombre,
    exist_ok=True,
    device=0,
)

mejor = f"/salida/{nombre}/weights/best.pt"
print(f"{nombre} SHA256:", hashlib.sha256(open(mejor, "rb").read()).hexdigest())
