"""Construye un video sintetico a partir de las imagenes de test de Zenodo,
para usarlo como camara simulada en la prueba de carga (punto 5) y de
latencia (punto 4) del plan de correcciones, ya que no hay acceso aqui a las
camaras RTSP reales de la municipalidad.
"""
import glob
import cv2

ORIGEN = "/origen"
SALIDA = "/salida/camara_simulada.mp4"
FPS = 5
TAMANO = (960, 540)

rutas = sorted(glob.glob(f"{ORIGEN}/*.jpg"))
print(f"{len(rutas)} imagenes encontradas")

writer = cv2.VideoWriter(SALIDA, cv2.VideoWriter_fourcc(*"mp4v"), FPS, TAMANO)

for i, ruta in enumerate(rutas):
    img = cv2.imread(ruta)
    if img is None:
        continue
    img = cv2.resize(img, TAMANO)
    writer.write(img)
    if i % 200 == 0:
        print(f"  {i}/{len(rutas)}")

writer.release()
print(f"Video guardado: {SALIDA} ({len(rutas)/FPS:.0f} segundos)")
