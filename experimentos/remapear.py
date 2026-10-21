"""Remapea las etiquetas del dataset externo 'Dangerous Items' (Zenodo,
5 clases) al esquema de 2 clases de Sentinel AI (arma_fuego=0, arma_blanca=1).

Mapeo verificado visualmente (no asumido):
    0 machete      -> 1 arma_blanca
    1 knife        -> 1 arma_blanca
    2 baseball bat -> (excluida: no es una clase de este proyecto)
    3 rifle        -> 0 arma_fuego
    4 gun          -> 0 arma_fuego

Las imagenes cuyo UNICO objeto es un bate quedan como fondo (etiqueta vacia),
no se descartan: siguen siendo utiles para medir falsos positivos.
"""
import shutil
from pathlib import Path

ORIGEN = Path("unpacked/Dangerous Items")
DESTINO = Path("eval_dataset")

MAPA = {0: 1, 1: 1, 3: 0, 4: 0}  # 2 (bat) se omite a proposito

SPLIT = "test"


def main():
    img_dst = DESTINO / "images" / SPLIT
    lbl_dst = DESTINO / "labels" / SPLIT
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    img_src = ORIGEN / "images" / SPLIT
    lbl_src = ORIGEN / "labels" / SPLIT

    n_img, n_obj_fuego, n_obj_blanca, n_bat_excluidos, n_img_bat_only = 0, 0, 0, 0, 0

    for txt in sorted(lbl_src.glob("*.txt")):
        lineas_out = []
        tenia_bat = False
        tenia_otra = False
        for linea in txt.read_text().splitlines():
            partes = linea.split()
            if not partes:
                continue
            cid = int(partes[0])
            if cid == 2:
                tenia_bat = True
                n_bat_excluidos += 1
                continue
            nuevo_id = MAPA.get(cid)
            if nuevo_id is None:
                continue
            tenia_otra = True
            partes[0] = str(nuevo_id)
            lineas_out.append(" ".join(partes))
            if nuevo_id == 0:
                n_obj_fuego += 1
            else:
                n_obj_blanca += 1

        if tenia_bat and not tenia_otra:
            n_img_bat_only += 1

        nombre = txt.stem
        img_origen = img_src / f"{nombre}.jpg"
        if not img_origen.exists():
            continue

        shutil.copy(img_origen, img_dst / img_origen.name)
        (lbl_dst / txt.name).write_text("\n".join(lineas_out))
        n_img += 1

    data_yaml = DESTINO / "data.yaml"
    data_yaml.write_text(
        "path: /data/eval_dataset\n"
        f"{SPLIT}: images/{SPLIT}\n"
        "train: images/test\n"  # ultralytics exige train/val; no se usan
        "val: images/test\n"
        "nc: 2\n"
        "names: ['arma_fuego', 'arma_blanca']\n"
    )

    print(f"Imagenes copiadas: {n_img}")
    print(f"Objetos arma_fuego (rifle+gun): {n_obj_fuego}")
    print(f"Objetos arma_blanca (machete+knife): {n_obj_blanca}")
    print(f"Cajas de bate excluidas: {n_bat_excluidos}")
    print(f"Imagenes donde el UNICO objeto era un bate (quedan sin etiquetas, como fondo): {n_img_bat_only}")


if __name__ == "__main__":
    main()
