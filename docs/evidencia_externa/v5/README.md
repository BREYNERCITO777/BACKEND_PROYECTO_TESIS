# Evidencia del modelo en producción (v5)

Test externo **sin duplicados** (1 054 imágenes de Dangerous Items, Zenodo, CC BY 4.0;
ver `ESTADO_CORRECCIONES_FRONTIERS.md`, punto 2). Reemplaza a la evidencia de v4 de la
carpeta superior.

- `confusion_matrix*.png`, `PR_curve.png`, `metricas_por_clase_conf025.json`: generados
  con `experimentos/evaluar_completo.py` a conf=0.25. Las cifras oficiales (conf=0.001)
  están en el punto 3 del documento de estado: mAP50 0.859, mAP50-95 0.545.
- `nivel_imagen.json`: al umbral de producción (0.65), 70.4% de las imágenes con arma
  disparan alerta (arma de fuego 74.4%, arma blanca 67.5%) y 1.05% de las imágenes sin
  arma dan falsa alarma (3 de 286).
- `puntos_operacion.json`: lo mismo para umbrales de 0.25 a 0.80.

## Casos de fallo

La métrica por cajas cuenta como error un arma detectada con la caja desplazada
(IoU < 0.5). Por eso estos casos se clasificaron mirándolos uno por uno:

| Archivo | Tipo | Qué pasa |
|---|---|---|
| `fn_cuchillo_desenfocado_ocluido.jpg` | Falso negativo real | Cuchillo fuera de foco y tapado por una mano en primer plano |
| `fn_cuchillo_cctv_baja_resolucion.jpg` | Falso negativo real | Cuchillo pequeño junto a la pierna, en CCTV de baja resolución |
| `fn_machete_luz_roja.jpg` | Falso negativo real | Machete bajo iluminación roja intensa |
| `fn_rifle_deportivo.jpg` | Falso negativo real | Rifle de tiro deportivo, forma poco común en el entrenamiento |
| `fp_bate_como_arma_fuego.jpg` | Falso positivo real | Bate de béisbol sostenido, confundido con arma de fuego |
| `localizacion_machete_caja_desplazada.jpg` | Caja desplazada | El machete se detecta, pero la caja no coincide con la anotación |

De los 6 primeros falsos positivos del test, 5 eran del tipo "caja desplazada" (el arma
correcta, con su anotación presente en el dataset) y solo 1 un error real (el bate).

Atribución del dataset: Omiotek, Z. (2025). *Electronics*, 14(17), 3540.
https://doi.org/10.3390/electronics14173540
