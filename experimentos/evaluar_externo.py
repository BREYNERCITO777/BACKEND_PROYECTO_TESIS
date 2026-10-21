"""Evaluacion en conjunto externo independiente (Reviewer 1, punto 1).

Corre el modelo v3 desplegado sobre el split 'test' del dataset publico
'Dangerous Items' (Zenodo, CC BY 4.0), remapeado a arma_fuego/arma_blanca.
Este dataset nunca fue usado para entrenar ni validar ningun modelo de este
proyecto (fuente distinta a Kaggle/DatasetNinja usados en el entrenamiento).

Cita requerida si se usa este dataset:
  Omiotek, Z. (2025). Effectiveness of Modern Models Belonging to the YOLO and
  Vision Transformer Architectures in Dangerous Items Detection.
  Electronics, 14(17), 3540. https://doi.org/10.3390/electronics14173540
"""
import json
from ultralytics import YOLO

MODELO = "/modelo/best.pt"
DATA_YAML = "/data/eval_dataset/data.yaml"

m = YOLO(MODELO)
print("Clases del modelo:", m.names)

met = m.val(data=DATA_YAML, split="test", conf=0.001, iou=0.5)

resultado = {
    "precision": float(met.box.mp),
    "recall": float(met.box.mr),
    "mAP50": float(met.box.map50),
    "mAP50_95": float(met.box.map),
    "por_clase": {
        m.names[i]: {"mAP50": float(met.box.ap50[i])}
        for i in range(len(m.names))
    },
}

print("=" * 60)
print("EVALUACION EN DATASET EXTERNO (nunca visto en train/val)")
print("=" * 60)
print(json.dumps(resultado, indent=2, ensure_ascii=False))

with open("/data/eval_dataset/resultado_externo.json", "w") as f:
    json.dump(resultado, f, indent=2, ensure_ascii=False)
