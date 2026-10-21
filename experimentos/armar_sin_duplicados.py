"""Crea copias del test externo y de sus degradaciones SIN las 194 imagenes que
son duplicados verificados de train/val de Zenodo (test_duplicados.txt) ni las
24 con extension .JPG que no pasaron por la verificacion de duplicados. Es el
subconjunto honesto para evaluar modelos que se entrenaron con Zenodo."""
import os
import shutil

BASE = "/w"
dups = set(open(f"{BASE}/test_duplicados.txt").read().split())
no_verificadas = {
    f[:-4] + ".jpg" for f in os.listdir(f"{BASE}/unpacked/Dangerous Items/images/test")
    if f.endswith(".JPG")
}
excluir = dups | no_verificadas
print(f"excluidas: {len(dups)} duplicadas + {len(no_verificadas)} sin verificar")

conjuntos = {"limpio": f"{BASE}/eval_dataset"}
for d in ("compresion", "blur", "oclusion", "desenfoque", "baja_luz"):
    conjuntos[d] = f"{BASE}/degradaciones/{d}"

for nombre, origen in conjuntos.items():
    destino = f"{BASE}/sin_duplicados/{nombre}"
    for sub in ("images", "labels"):
        os.makedirs(f"{destino}/{sub}/test", exist_ok=True)
    n = 0
    for img in os.listdir(f"{origen}/images/test"):
        if img in excluir:
            continue
        shutil.copy(f"{origen}/images/test/{img}", f"{destino}/images/test/{img}")
        lbl = os.path.splitext(img)[0] + ".txt"
        src_lbl = f"{origen}/labels/test/{lbl}"
        if os.path.exists(src_lbl):
            shutil.copy(src_lbl, f"{destino}/labels/test/{lbl}")
        n += 1
    with open(f"{destino}/data.yaml", "w") as f:
        f.write(f"path: /ext/sin_duplicados/{nombre}\n"
                "test: images/test\ntrain: images/test\nval: images/test\n"
                "nc: 2\nnames: ['arma_fuego', 'arma_blanca']\n")
    print(f"{nombre}: {n} imagenes")
