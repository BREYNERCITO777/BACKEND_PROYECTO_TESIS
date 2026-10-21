"""v5: ajuste fino de v4 agregando copias con blur de movimiento y oclusion
aleatorios (generar_aumentos.py). Mismo protocolo que v4 para que la unica
diferencia sea el aumento de datos."""
import hashlib
from ultralytics import YOLO

YOLO("/modelo/best.pt").train(
    data="/eval/data_v5.yaml",
    epochs=20,
    imgsz=640,
    batch=16,
    lr0=0.001,
    close_mosaic=8,
    patience=8,
    seed=0,
    workers=4,
    project="/salida",
    name="modelo_v5",
    exist_ok=True,
    device=0,
)

mejor = "/salida/modelo_v5/weights/best.pt"
print("modelo_v5 SHA256:", hashlib.sha256(open(mejor, "rb").read()).hexdigest())
