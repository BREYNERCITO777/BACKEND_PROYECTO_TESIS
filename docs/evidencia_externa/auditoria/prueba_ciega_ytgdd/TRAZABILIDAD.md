# Trazabilidad de la prueba ciega (YouTube-GDD)

| Paso | Evidencia | Hora (America/Lima, -05:00) |
|---|---|---|
| Protocolo escrito | `PROTOCOLO.md`, línea "Escrito: 2026-10-29T20:27:42Z" | 15:27:42 |
| Única evaluación | `resultado_ciego.json` y `salida/v5/*.png` (curvas y matrices de Ultralytics) | 15:28:09 – 15:28:20 |
| Nota posterior en el protocolo | corrección de una suma (42,866 -> 43,266), al final de `PROTOCOLO.md` | 15:32 (por eso cambia la fecha de modificación del archivo) |

- Pesos: `salida_noche/modelo_v5/weights/best.pt`,
  SHA-256 `1aec8d3c923cc0a02f0fae5b435d456a790dd86daeb19fd747267f3cda8b6621` (el modelo desplegado).
- Imágenes: `manifiesto_ytgdd_test.csv` — los 500 archivos con su vídeo de YouTube, SHA-256 y número
  de cajas de arma. 500 fotogramas de 42 vídeos (hasta 80 por vídeo); 497 con arma, 879 cajas, 3 sin arma.
- Origen: split de test oficial de https://github.com/UCAS-GYX/YouTube-GDD (etiquetas
  `YouTube-GDD_test_labels.zip`, Apache-2.0; imágenes del enlace de Google Drive del README).
- Comando (una sola vez, imagen `sentinel-backend:1.0.0`, Ultralytics 8.3.40):

```
docker run --rm --gpus all --shm-size=2g \
  -v ".../salida_noche/modelo_v5/weights:/modelo:ro" -v ".../dataset_ciego_ytgdd:/ciego" \
  sentinel-backend:1.0.0 python /ciego/evaluar_ciego.py
```

- Parámetros: `conf=0.001, iou=0.5, batch=8, workers=2, imgsz=640` (igual que la Tabla 4); alertas a
  nivel de imagen con `conf=0.65`.
- Resultado: P 0.7943, R 0.4699, AP50 0.5840, AP50-95 0.3870; 497 imágenes con arma: 252 con
  alguna alerta, de ellas 10 solo como arma blanca, es decir 242 (48.7 %) con alerta como arma de fuego.
- Deduplicación previa: `dedup_ciego.json` (dHash, Hamming <= 6, contra 43,266 imágenes) y
  `candidatos_verificados.json` (3 candidatos, MAD 26–115 frente al umbral 4: ninguno es copia).
- No hubo ninguna inferencia previa sobre este conjunto ni ajuste posterior: el modelo, los
  umbrales y el conjunto no cambiaron después de ver el resultado.
