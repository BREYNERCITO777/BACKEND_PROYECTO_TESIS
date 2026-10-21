"""Verifica que v4 no reintrodujo el falso positivo de motos que v3 ya habia
corregido, ni el de lienzos vacios del modelo original."""
import numpy as np
from ultralytics import YOLO
import cv2

m = YOLO("/modelo/best.pt")

print("--- Prueba de lienzos vacios (no deberia detectar nada) ---")
pruebas = {
    "lienzo blanco": np.full((640, 640, 3), 255, np.uint8),
    "lienzo negro": np.zeros((640, 640, 3), np.uint8),
    "gris uniforme": np.full((640, 640, 3), 128, np.uint8),
    "ruido aleatorio": np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8),
}
fallos = 0
for nombre, img in pruebas.items():
    r = m(img, verbose=False)[0]
    dets = [(m.names[int(b.cls[0])], round(float(b.conf[0]), 2)) for b in r.boxes]
    if dets:
        fallos += 1
        print(f"  {nombre:18s} -> FALSO POSITIVO: {dets}")
    else:
        print(f"  {nombre:18s} -> sin detecciones (correcto)")

print()
print("--- Prueba de la mototaxi (no deberia detectar arma_fuego) ---")
img = cv2.imread("/eval/mototaxi.png")
if img is None:
    print("  No se pudo leer mototaxi.png")
else:
    r = m(img, verbose=False)[0]
    dets = [(m.names[int(b.cls[0])], round(float(b.conf[0]), 2)) for b in r.boxes]
    if dets:
        print(f"  FALSO POSITIVO: {dets}")
    else:
        print("  sin detecciones (correcto)")
