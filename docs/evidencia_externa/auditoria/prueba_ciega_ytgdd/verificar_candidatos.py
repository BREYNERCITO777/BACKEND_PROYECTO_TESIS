import json, cv2, numpy as np, glob, os
d = json.load(open("/ciego/dedup_ciego.json"))
F = {"propio_train": "/data/dataset_80_20/train/images", "propio_val": "/data/dataset_80_20/val/images",
     "zenodo_train": "/zen/train_dataset/images/train", "copias_aumentadas_v5": "/zen/aug_dataset/images/train"}
def g(p): return cv2.resize(cv2.imread(p, cv2.IMREAD_GRAYSCALE), (64, 64), interpolation=cv2.INTER_AREA).astype(float)
filas = []
out = {}
for t, cands in d["candidatos"].items():
    a = cv2.imread(f"/ciego/ytgdd_test/images/test/{t}")
    for fuente, nombre, dist in cands:
        p = os.path.join(F[fuente], nombre)
        mad = float(np.abs(g(f"/ciego/ytgdd_test/images/test/{t}") - g(p)).mean())
        out.setdefault(t, []).append({"fuente": fuente, "archivo": nombre, "hamming": dist, "mad": round(mad, 2),
                                      "duplicado": mad < 4})
        b = cv2.imread(p)
        fila = np.hstack([cv2.resize(a, (320, 240)), cv2.resize(b, (320, 240))])
        cv2.putText(fila, f"MAD {mad:.1f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        filas.append(fila)
cv2.imwrite("/ciego/candidatos.jpg", np.vstack(filas))
json.dump(out, open("/ciego/candidatos_verificados.json", "w"), indent=1)
print(json.dumps(out, indent=1))
