"""Renderiza figN.html (1000 px de ancho, escala 3 = 3000 px) con Edge headless,
recorta el blanco sobrante y guarda PNG y TIFF RGB a 300 dpi (a 180 mm de ancho
el texto minimo de 16 px queda en unos 8 pt).
Uso: python render.py fig2 [fig3 ...]"""
import os, subprocess, sys
from PIL import Image, ImageChops
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "final")
for nombre in sys.argv[1:]:
    png = os.path.join(AQUI, f"{nombre}_bruto.png")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=3",
                    "--virtual-time-budget=2000", "--window-size=1000,1400", f"--screenshot={png}",
                    "file:///" + os.path.join(AQUI, f"{nombre}.html").replace("\\", "/")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=120)
    im = Image.open(png).convert("RGB")
    fondo = Image.new("RGB", im.size, (255, 255, 255))
    x0, y0, x1, y1 = ImageChops.difference(im, fondo).getbbox()
    im = im.crop((0, 0, im.width, min(im.height, y1 + 30)))
    num = int(nombre.replace("fig", ""))
    for ext in ("png", "tiff"):
        im.save(os.path.join(SALIDA, f"Figura_{num:02d}.{ext}"), dpi=(300, 300),
                **({"compression": "tiff_lzw"} if ext == "tiff" else {}))
    os.remove(png)
    print(nombre, im.size, "alto recortado", "de", 4200, "->", im.height, "(si es 4200, ampliar --window-size)")
