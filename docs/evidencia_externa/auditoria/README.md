# Evidencia de las auditorías V7→V11 (29-30 oct 2026)

Respaldo de las cifras corregidas con datos reales, no con redacción. Todo lo
numérico de la Tabla 5 y de la latencia extremo a extremo se regenera con:

```
python recalcular.py
```

Regla única en todas las cifras de latencia: se descarta el primer lote de cada
corrida (inicialización de CUDA y del modelo, 2.3-3.5 s) y los percentiles son
por rango más cercano. Con eso el script devuelve exactamente lo que dice el
manuscrito V11.

## `logs_fps_timestamps/` (Tabla 5)
Logs crudos de `docker logs -t` (marca de tiempo real por línea) de 8 pruebas de
carga (1/4/8/16 cámaras simuladas, GPU y CPU), corridas el 29 de octubre de 2026
sobre `sentinel-agent:1.0.0` y el modelo v5 desplegado (SHA256 `1aec8d3c…`).

- **FPS por cámara** = líneas `LATENCIA_FRAME` / (última marca − primera) / N.
  El agente imprime `LATENCIA_FRAME` *después* de la inferencia, así que son
  fotogramas analizados, no capturados.
- **Duración real** entre el primer y el último fotograma analizado: 65.5-67.5 s
  en GPU; 65.5, 70.0, 84.2 y 114.2 s en CPU con 1, 4, 8 y 16 cámaras.
- Reemplaza al cálculo anterior (`analizar_carga.sh`), que restaba 15 s fijos y
  por eso sobreestimaba el FPS (5.8-5.9 en vez de 4.93-4.99).

## `logs_latencia_e2e/` (latencia captura → alerta en MongoDB + WebSocket)
Una línea `LATENCIA ... total_agente_ms=` por alerta: inferencia + codificación
de la evidencia + ida y vuelta HTTP hasta que el backend responde, y el backend
responde después de guardar el incidente en MongoDB y emitir por WebSocket
(`app/routers/agent.py`).

| Carga | Archivo | Alertas usadas | Descartadas (calentamiento) | P50 / P95 (ms) |
|---|---|---|---|---|
| 1 cámara GPU | `latencia_multigpu_1.txt` | 16 | 1 | 57 / 65 |
| 4 cámaras GPU | `e2e_log_4.txt` | 44 | 4 | 106 / 177 |
| 8 cámaras GPU | `e2e_log_8.txt` | 104 | 0 | 122 / 147 |
| 16 cámaras GPU | `latencia_multigpu_16.txt` | 272 | 0 | 151 / 190 |
| 1 cámara CPU | `latencia_multicpu_1.txt` | 17 | 0 | 130 / 154 |

El P95 con 4 cámaras (177) queda por encima del de 8 (147) porque sale de solo
44 alertas y lo fijan unas pocas lentas; no es un error de cálculo. Estas
latencias son solo de fotogramas que generaron alerta (máximo una por cámara
cada 5 s) y no son la latencia de inferencia por lote de la Tabla 5.

## `metricas_sin_redondear/` (Tabla 4)
Salida completa (sin redondear) de `m.val(conf=0.001, iou=0.5)` sobre el modelo
v5 verificado por SHA256:
- `metricas_por_clase_1054.json`: conjunto de prueba depurado oficial.
- `metricas_por_clase_1078.json`: + los 24 `.JPG` verificados (sensibilidad).

Reemplaza la corrida anterior, que había usado `conf=0.25` por error y por eso el
mAP@0.5:0.95 por clase no promediaba el valor global.

Fila v5 y filas por clase de la Tabla 4 (V13): misma corrida, `batch=8, workers=2`, igual que la
evaluación original (`cola_noche/evaluar_todo.py`). `metricas_mismo_lote.json` reproduce exactamente
la fila v5 (P 0.8631, R 0.7949, mAP50 0.8592, mAP50-95 0.5449) y da las filas por clase. Con
`batch=16` cambian precisión y recall hasta 0.003 (el lote cambia el relleno de las imágenes):
esa es la corrida de `metricas_por_clase_1054.json`.

## `jpg24_resultado.json`
Los 24 `.JPG` (mayúscula) del test de Zenodo —omitidos por el filtro original
sensible a mayúsculas— comparados contra las cuatro fuentes de entrenamiento
(21,534 + 5,386 + 5,934 + 1,272 imágenes) con el mismo dHash y umbral 6 de
`experimentos/duplicados_phash.py`. Ninguno es duplicado.

## `deduplicacion/` (traza de las 194 + 24 imágenes)
- `test_duplicados.txt`: las 194 imágenes de test descartadas por ser copia de
  una imagen de entrenamiento (160) o validación (34) de Zenodo.
- `duplicados_verificados.json`: los 474 candidatos del dHash (distancia de
  Hamming ≤ 6) con su imagen pareja, la distancia y la diferencia media por
  píxel de la segunda comprobación; solo los que la pasan quedan en la lista.
- `duplicados_test_externo.json`: resumen de la corrida (1,248 imágenes de test
  leídas, umbral 6).
- `manifiesto_limpio.csv`: las 1,054 imágenes del test final con su SHA-256 y si
  tienen arma (768 con arma, 286 sin arma).
- `manifiesto_limpio_1078.csv`: lo mismo con los 24 `.JPG` añadidos (los 24 son
  imágenes sin arma: 768 / 310).
- Scripts (en `experimentos/`): `duplicados_phash.py`, `verificar_duplicados.py`,
  `armar_sin_duplicados.py`, `revisar_24_jpg.py`.

## `prueba_ciega_ytgdd/` (prueba ciega, V13)
v5 evaluado UNA vez en el test oficial de YouTube-GDD (500 fotogramas, 879 armas de fuego), que
nunca se usó para entrenar ni elegir modelos. `PROTOCOLO.md` se escribió antes de evaluar (con una
nota posterior que corrige una suma). Deduplicación contra las 43,266 imágenes que vio v5: 3
candidatos de dHash, ninguno duplicado a nivel de píxel. Resultado: P 0.794, R 0.470, AP50 0.584,
AP50-95 0.387; 252/497 imágenes con arma disparan alerta a 0.65. Las imágenes no se incluyen
(fotogramas de YouTube); se descargan del repositorio de YouTube-GDD.

## `logs_latencia_cliente_ws/` (latencia hasta un cliente WebSocket, V13)
Backend y MongoDB desechables, un cliente WebSocket suscrito a `/api/v1/ws/alerts` y el agente con
1/4/8/16 cámaras en GPU. `python analizar_e2e_cliente.py` empareja cada mensaje con su alerta por
cámara y marca de tiempo: captura→cliente P50/P95 = 55/61, 111/128, 130/148 y 159/193 ms
(17, 65, 131 y 227 alertas).

## Lo que no se puede verificar con estos archivos
- **Separación temporal** entre los 404 fotogramas de entrenamiento (24 ago 2026)
  y los 5,772 de la prueba de campo: no se registró en su momento. El manuscrito
  lo declara como limitación (sexta limitación en la Discusión).
- **Retención durante la evaluación**: la purga automática
  (`EVIDENCE_RETENTION_DAYS`) se agregó al código el 21 oct 2026, después de la
  evaluación, y vale 0 (desactivada) por defecto. Las imágenes de evidencia de la
  evaluación siguen en MongoDB Atlas hasta que se borren a mano.
