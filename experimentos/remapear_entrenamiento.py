"""Remapea train/val del dataset externo 'Dangerous Items' (Zenodo) al esquema
de 2 clases de Sentinel AI, para usarlos como datos de entrenamiento.

A proposito deja el split 'test' sin tocar: es el conjunto de evaluacion
independiente ya usado para medir el mAP real (ver evaluar_externo.py /
ESTADO_CORRECCIONES_FRONTIERS.md, punto 2). Si se mezclara test aqui, se
volveria a contaminar la unica medicion honesta que existe.

Mismo mapeo verificado visualmente que remapear.py:
    0 machete -> 1 arma_blanca   1 knife -> 1 arma_blanca
    3 rifle   -> 0 arma_fuego    4 gun   -> 0 arma_fuego
    2 baseball bat -> excluida (no es clase del sistema)
"""
import shutil
from pathlib import Path

ORIGEN = Path("unpacked/Dangerous Items")
DESTINO = Path("train_dataset")
MAPA = {0: 1, 1: 1, 3: 0, 4: 0}
SPLITS = ["train", "val"]


def procesar_split(split):
    img_dst = DESTINO / "images" / split
    lbl_dst = DESTINO / "labels" / split
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    img_src = ORIGEN / "images" / split
    lbl_src = ORIGEN / "labels" / split

    n_img = 0
    for txt in sorted(lbl_src.glob("*.txt")):
        lineas_out = []
        for linea in txt.read_text().splitlines():
            partes = linea.split()
            if not partes:
                continue
            cid = int(partes[0])
            nuevo_id = MAPA.get(cid)
            if nuevo_id is None:  # bate: se descarta la caja
                continue
            partes[0] = str(nuevo_id)
            lineas_out.append(" ".join(partes))

        nombre = txt.stem
        img_origen = img_src / f"{nombre}.jpg"
        if not img_origen.exists():
            continue

        shutil.copy(img_origen, img_dst / img_origen.name)
        (lbl_dst / txt.name).write_text("\n".join(lineas_out))
        n_img += 1

    return n_img


def main():
    for split in SPLITS:
        n = procesar_split(split)
        print(f"{split}: {n} imagenes remapeadas y copiadas a {DESTINO}/images/{split}")


if __name__ == "__main__":
    main()
