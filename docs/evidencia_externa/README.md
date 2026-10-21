# Evidencia de la evaluación externa (modelo v4)

Generado con `dataset_externo_zenodo/evaluar_completo.py` contra el split `test`
(1272 imágenes) del dataset público **"Dangerous Items"** (Zenodo, DOI
10.5281/zenodo.16422779), nunca usado en entrenamiento. Ver
`ESTADO_CORRECCIONES_FRONTIERS.md`, punto 2, para el contexto completo.

- `metricas_por_clase.json` — precision/recall/mAP50/mAP50-95 global y por clase.
- `confusion_matrix.png` / `confusion_matrix_normalized.png` — matriz de confusión.
- `falso_negativo_cuchillo_borroso.jpg` — cuchillo no detectado por desenfoque +
  oclusión parcial.
- `falso_positivo_bate.jpg` — bate de béisbol (clase excluida del sistema de 2
  clases) confundido con `arma_blanca`.

**Atribución requerida por la licencia del dataset (CC BY 4.0):** Omiotek, Z.
(2025). Effectiveness of Modern Models Belonging to the YOLO and Vision
Transformer Architectures in Dangerous Items Detection. *Electronics*, 14(17),
3540. https://doi.org/10.3390/electronics14173540
