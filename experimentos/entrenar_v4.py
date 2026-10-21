"""Ajuste fino de v3 incorporando datos externos diversos (Zenodo 'Dangerous
Items', train+val) para mejorar el recall real medido en el punto 2 del plan
de correcciones (mAP50 externo cayo a 0.33 porque el modelo solo habia visto
camaras municipales).

Parte de v3 (no desde cero) para no perder el arreglo de falsos positivos con
motos. El split 'test' de Zenodo NUNCA entra aqui -- es el conjunto de
evaluacion independiente que hay que poder seguir citando limpio.
"""
import hashlib
from ultralytics import YOLO

MODELO_BASE = "/modelo/best.pt"
DATA = "/eval/data_combinado.yaml"

m = YOLO(MODELO_BASE)

results = m.train(
    data=DATA,
    epochs=20,
    imgsz=640,
    batch=16,
    lr0=0.001,
    close_mosaic=8,
    patience=8,
    project="/salida",
    name="modelo_v4",
    exist_ok=True,
    device=0,
)

mejor = "/salida/modelo_v4/weights/best.pt"
print("=" * 60)
print("ENTRENAMIENTO v4 TERMINADO")
print("SHA256:", hashlib.sha256(open(mejor, "rb").read()).hexdigest())
print("=" * 60)
