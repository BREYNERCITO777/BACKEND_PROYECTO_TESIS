# Estado real del plan de correcciones — Frontiers (Manuscript ID 1919959)

> Verificado contra el código, los commits, el dataset y los modelos en disco.
> No se afirma nada aquí que no tenga evidencia reproducible detrás.
> Fecha límite: 30 de octubre de 2026.

Leyenda: ✅ Resuelto con evidencia · ⚠️ Parcial / requiere trabajo adicional · ❌ Pendiente, necesita datos o decisión externa

---

## PRIORIDAD 1 — CRÍTICA

### 1. Confirmar entrenamiento 20 vs 100 épocas — ✅ Resuelto
El entrenamiento original (CPU) se detuvo en la época 7 de 10 sin converger, y además
`close_mosaic=10` desactivaba el aumento por mosaico desde la primera época (error de
configuración). Se corrigió con dos entrenamientos documentados:

- **v2**: YOLOv8s, 60 épocas, GPU RTX 2070, dataset 80/20 (21 211/5 305 img) → mAP50 0.957
- **v3**: ajuste fino de v2, +20 épocas, con 404 imágenes de fondo reales de calle, para
  corregir falsos positivos (ver punto 6)

Evidencia: `reentrenamiento/metodologia_particion.md`, `reentrenamiento/LEEME.md`,
`results.csv` de ambos modelos, hashes SHA256 verificados.

**Hallazgo y corrección aplicada hoy:** `app/models/best.pt` del backend y
`sentinel-agent/best.pt` estaban desincronizados en la copia exportada
`BACKEND_PROYECTO_TESIS-main` (modelo viejo roto, antes de v2). Corregido a v3. El
repositorio real (`repo-github`) y la imagen Docker en producción (`tesis-backend:local`,
build 24-ago) ya tenían v3 correctamente.

**Pendiente:** trasladar esta cronología al manuscrito (sección de metodología).

### 2. Evaluación en conjunto externo independiente — ✅ Resuelto (resultado delicado, ver abajo)
**El split "test" que el notebook llama "nunca visto" en realidad SÍ fue usado para
entrenar v2/v3.** Verificado por nombre de archivo: las 2 564 imágenes de
`dataset_final/test` están 100 % contenidas dentro de `dataset_80_20/train`+`val`
(solapamiento confirmado por comparación de nombres de archivo).

Esto significa que **ninguna de las métricas reportadas hasta ahora (mAP 0.957, etc.)
está validada en datos realmente no vistos** por el modelo desplegado. Es exactamente
lo que señala el Reviewer 1, punto 1.

Existe un archivo `app/models/best_externo.pt` en el repo desde el primer commit, pero
no está referenciado en ningún código ni tiene registro de evaluación — es un archivo
huérfano, no una evaluación hecha. **Retirado del repositorio** junto con `yolov8n.pt`
(pesos COCO genéricos que Ultralytics descarga solo); copia con SHA256 en
`D:\TESIS BREYNER\respaldo_modelos_repo\` y en el historial de git.

**Resuelto hoy.** Se evaluó el modelo v3 desplegado sobre el dataset público
["Dangerous Items" (Zenodo, DOI 10.5281/zenodo.16422779)](https://zenodo.org/records/16422779),
CC BY 4.0, de la Universidad Tecnológica de Lublin — fuente distinta a Kaggle/
DatasetNinja usados en el entrenamiento, por lo que es una evaluación genuinamente
independiente. 1272 imágenes del split "test" oficial del dataset externo, remapeadas
de sus 5 clases (machete, knife, baseball bat, rifle, gun) a las 2 del proyecto
(arma_fuego = rifle+gun, arma_blanca = machete+knife; las 276 cajas de "baseball bat"
se excluyeron por no ser una clase del sistema — mapeo verificado visualmente, no
asumido).

**Resultado — caída fuerte frente a la validación interna:**

| Métrica | Validación interna (contaminada) | **Externo (independiente)** |
|---|---|---|
| Precision | 0.927 | **0.541** |
| Recall | 0.926 | **0.314** |
| mAP50 | 0.957 | **0.329** |
| mAP50-95 | 0.713 | **0.160** |
| mAP50 arma_fuego | — | 0.370 |
| mAP50 arma_blanca | — | 0.287 |

El recall de 0.314 significa que el modelo **deja de detectar aproximadamente 7 de
cada 10 armas** en escenas que nunca vio durante el entrenamiento. La caída es
consistente con un problema de dominio: el dataset externo son fotos de stock/CCTV de
tiendas y defensa personal, con iluminación, ángulos y resolución muy distintos a las
cámaras municipales de la calle con las que se entrenó el modelo real.

**Esto es exactamente lo que dice el Reviewer 1** y conviene reportarlo así de
directo en la respuesta: las métricas de 0.95+ eran de un split contaminado: la
cifra honesta y citable es ~0.33 de mAP50 en datos externos. Script y datos:
`dataset_externo_zenodo/` (fuera del repo, en disco local), remapeo en
`remapear.py`, evaluación en `evaluar_externo.py`.

### Actualización — modelo v4 (ajuste fino con datos externos, desplegado)

Se incorporaron los splits `train`+`val` del mismo dataset Zenodo (remapeados,
`remapear_entrenamiento.py`) al entrenamiento, combinados con el dataset propio, y se
hizo ajuste fino de v3 por 20 épocas (`entrenar_v4.py`, 3.53 h en RTX 2070). **El
split `test` de Zenodo nunca se usó para entrenar** — sigue siendo la medición
independiente.

**Resultado en el test de Zenodo (nunca visto en ningún entrenamiento):**

| Métrica | v3 | **v4** |
|---|---|---|
| Precision | 0.541 | **0.890** |
| Recall | 0.314 | **0.800** |
| mAP50 | 0.329 | **0.878** |
| mAP50-95 | 0.160 | **0.584** |

**Pruebas de regresión (que v4 no reintrodujera fallos ya corregidos) — todas
pasaron:** sin falsos positivos en lienzos blanco/negro/gris/ruido, sin falso
positivo en la foto de la mototaxi que v3 ya había corregido.

**v4 desplegado** en `app/models/best.pt`, `sentinel-agent/best.pt` e imagen
`tesis-backend:local`, hash `c7267b86...`, verificado en los tres sitios.

### Ampliación — precision/recall por clase, matriz de confusión y fallos representativos

El texto literal del Reviewer 1 (punto 1, confirmado por el usuario con el comentario
original de Frontiers, no solo el resumen del plan) pide explícitamente *"per‑class
precision/recall, confusion matrices, and representative failure cases"* — no solo
mAP. Se completó:

**Precision/recall por clase (test externo, v4, conf=0.25):**

| Clase | Precision | Recall | mAP50 |
|---|---|---|---|
| arma_fuego | 0.904 | 0.830 | 0.896 |
| arma_blanca | 0.876 | 0.769 | 0.855 |

**Matriz de confusión:** generada en
`dataset_externo_zenodo/eval_dataset/val_completo/confusion_matrix_normalized.png`.
La diagonal confirma el recall por clase (0.85 / 0.80). **Ojo con la columna
"background"**: no significa "61% de los fondos fallan" — es el reparto de falsos
positivos entre clases, normalizado de una forma que hay que explicar con cuidado en
el texto (es el mismo tipo de confusión que señaló el Reviewer 4 en el punto 12).

**Casos de fallo representativos** (`dataset_externo_zenodo/eval_dataset/fallos/`,
6 falsos negativos + 6 falsos positivos guardados con la caja dibujada):

- **Falso negativo típico:** cuchillo borroso (persona de fondo fuera de foco) y
  parcialmente oculto por una mano en primer plano — se pierde por desenfoque +
  oclusión simultáneos.
- **Falso positivo con bate de béisbol** (clase excluida del sistema de 2 clases),
  confundido con `arma_blanca` a umbral 0.25. **Corrección posterior:** una versión
  anterior de este documento decía que el entrenamiento "nunca vio un bate como
  negativo". Era falso: 955 imágenes de solo-bate entraron al entrenamiento de v4
  como fondo (etiqueta vacía), más 205 en validación. Medido sobre las 212 imágenes
  de test que solo contienen un bate (`medir_bates.py`):

  | Umbral | Imágenes con falso positivo |
  |---|---|
  | 0.25 (evaluación) | 20/212 (9.4%) |
  | **0.65 (producción)** | **1/212 (0.5%)** |

  Al umbral real de operación el problema es marginal. Se reporta como observación
  menor, no como limitación principal, y no justifica reentrenar.

Script: `dataset_externo_zenodo/evaluar_completo.py`. Evidencia versionada en
`docs/evidencia_externa/` (matriz de confusión, 2 casos de fallo, métricas en JSON).

### Hallazgo — duplicados dentro del propio dataset Zenodo

El revisor pide descartar duplicados. Se compararon las imágenes del test externo contra
todos los conjuntos de entrenamiento (`duplicados_phash.py` + `verificar_duplicados.py`):

1. dHash de 64 bits: 474 candidatos. **Demasiado permisivo**: a distancia 2 ya empareja
   cuchillos distintos fotografiados con la misma composición (producto en diagonal sobre
   fondo blanco). Se revisaron pares a ojo.
2. Verificación fina (diferencia media de grises a 64×64): distribución bimodal clara —
   190 pares con diferencia < 2, casi nada entre 2 y 6, luego crece. Corte en < 4.

| Origen del duplicado | Imágenes de test |
|---|---|
| train de Zenodo | 160 |
| val de Zenodo | 34 |
| Dataset propio (Kaggle/DatasetNinja) | **0** |
| **Total** | **194 de 1 248 (15.5%)** |

El propio dataset de Zenodo tiene copias de la misma foto (p. ej. un machete de catálogo
en dos resoluciones) en sus particiones de train y de test.

**Consecuencias:**
- **v3 (0.329) es una cifra limpia**: nunca vio Zenodo y no hay duplicados con el dataset
  propio.
- **v4 (0.878) y YOLOv5s están inflados**: entrenaron con train/val de Zenodo, así que
  ya vieron esas 194 imágenes.
- Se armó el subconjunto **sin duplicados** (`armar_sin_duplicados.py`): 1 054 imágenes
  (se excluyen además 24 archivos `.JPG` en mayúscula que no pasaron por la
  verificación). **Todas las cifras finales del manuscrito deben salir de ese
  subconjunto.** La evaluación de la cola nocturna ya lo usa como medida principal.

**Nota metodológica para el manuscrito:** v4 ya no es una evaluación "100%
independiente del pipeline" en el sentido de que el dataset externo fue usado
parcialmente para entrenar — pero el split de prueba usado para medir (`test`)
nunca entró al entrenamiento, así que la cifra de 0.878 mAP50 sigue siendo honesta
y defendible como held-out. Conviene explicar esta distinción explícitamente al
reviewer: "se amplió el conjunto de entrenamiento con datos externos diversos para
cerrar la brecha de dominio detectada, y se validó en el split de prueba oficial
de esa fuente, nunca usado en el ajuste fino".

**Citar si se usa este dataset:** Omiotek, Z. (2025). Effectiveness of Modern Models
Belonging to the YOLO and Vision Transformer Architectures in Dangerous Items
Detection. *Electronics*, 14(17), 3540. https://doi.org/10.3390/electronics14173540

### 3. Comparar YOLOv8 contra otro detector — ✅ Resuelto (comparación justa, versión final)

**Esta subsección reemplaza a la tabla de más abajo**, que comparaba v4 (ajuste fino desde
v3) con YOLOv5s (desde COCO) — inicializaciones distintas — y sobre un test con 194
duplicados. Ahora YOLOv8n, YOLOv8s y YOLOv5s parten todos de pesos COCO, con el mismo
dataset combinado, 20 épocas, batch 16, imgsz 640, semilla 0; evaluados con el mismo
protocolo (conf 0.001, IoU NMS 0.5) sobre las **1 054 imágenes del test externo sin
duplicados**. El manuscrito dice YOLOv8n; desde v2 el modelo desplegado es YOLOv8s.

| Modelo | Inicialización | Precision | Recall | mAP50 | mAP50-95 | GPU P50 / P95 | CPU P50 / P95 |
|---|---|---|---|---|---|---|---|
| YOLOv8n | COCO | 0.830 | 0.714 | 0.795 | 0.460 | 13.6 / 31.9 ms | **53.7 / 74.8 ms** |
| YOLOv5s | COCO | 0.830 | **0.792** | 0.838 | 0.461 | 17.7 / 32.1 ms | 98.4 / 135.8 ms |
| YOLOv8s | COCO | **0.885** | 0.755 | **0.854** | 0.516 | 16.4 / 32.8 ms | 128.7 / 179.0 ms |
| v4 (producción, YOLOv8s) | ajuste fino de v3 | 0.854 | 0.778 | 0.847 | **0.531** | 14.3 / 25.7 ms | 130.5 / 182.5 ms |
| v3 (anterior) | — | 0.558 | 0.315 | 0.334 | 0.162 | — | — |

Latencia (`benchmark_latencia.py`): una imagen por vez, de punta a punta
(preprocesamiento + inferencia + NMS), 200 imágenes tras 20 de calentamiento, RTX 2070 y
CPU de la misma laptop (torch 6 hilos).

**Lectura para responder al revisor:**
- **YOLOv8n no es el más preciso**: 4 puntos de mAP50 debajo de YOLOv5s y 6 debajo de
  YOLOv8s.
- **YOLOv8n es ~2× más rápido en CPU** (54 ms vs. 98-130 ms). En GPU todos están entre
  14 y 18 ms y la ventaja desaparece.
- Por lo tanto la afirmación del manuscrito solo se sostiene para despliegue **sin
  GPU**. Con GPU (necesaria igual para más de 1 cámara, ver #5), YOLOv8s es la mejor
  opción. El manuscrito debe decir YOLOv8s y justificarlo con esta tabla.
- v4 (desde v3) y YOLOv8s (desde COCO) empatan en el test limpio; el ajuste fino desde
  v3 no aportó precisión.

Robustez de los mismos modelos (mAP50, test sin duplicados; ver #6):

| Modelo | Limpio | Compresión | Blur | Oclusión | Desenfoque | Baja luz |
|---|---|---|---|---|---|---|
| v3 | 0.334 | 0.314 | 0.171 | 0.059 | 0.222 | 0.240 |
| YOLOv8n | 0.795 | 0.729 | 0.451 | 0.187 | 0.603 | 0.575 |
| YOLOv5s | 0.838 | 0.738 | 0.400 | 0.238 | 0.618 | 0.581 |
| YOLOv8s | 0.854 | 0.789 | 0.473 | 0.205 | 0.641 | **0.658** |
| v4 | 0.847 | 0.777 | 0.468 | 0.207 | 0.633 | **0.497** |
| **v5 (v4 + aumentos)** | **0.859** | **0.811** | **0.674** | **0.505** | **0.748** | 0.553 |

YOLOv8s desde COCO supera a v4 por 16 puntos en baja luz con la misma precisión en
limpio: partir de v3 parece haberle restado robustez.

**v5** (`cola_noche/entrenar_v5.py`): ajuste fino de v4 por 20 épocas agregando 8 240
copias del conjunto de entrenamiento con motion blur y oclusión aleatorios
(`generar_aumentos.py`). Se cayó por memoria en la época 5 (otro contenedor ocupaba
4.4 GB de la VM) y se **retomó desde la época 4** con `resume=True`. En limpio:
P=0.863, R=0.795, mAP50-95=0.545; recall arma_fuego 0.833, arma_blanca 0.757.

- Blur (+21 pts) y oclusión (+30 pts) mejoran mucho, pero **en parte es circular**: v5
  entrenó con esos mismos tipos de degradación (con parámetros aleatorios, distintos de
  los fijos de la evaluación).
- **Desenfoque, que ningún modelo vio al entrenar: +11.5 pts.** La mejora generaliza.
- Baja luz: +5.6 pts sobre v4, pero YOLOv8s-COCO sigue siendo el mejor ahí (0.658).
- Sin pérdida en limpio (0.859 vs. 0.847).

**v5 desplegado en producción** (reemplaza a v4), SHA256 `1aec8d3c…`, tras pasar las
pruebas de regresión:

| Prueba | v4 | v5 |
|---|---|---|
| Lienzos blanco/negro/gris/ruido | 0 detecciones | 0 detecciones |
| Mototaxi de la vía real | 0 detecciones | 0 detecciones |
| Bates (212 imágenes) a umbral 0.65 | 1 falso positivo (0.5%) | 3 falsos positivos (1.4%) |
| Cámara real al anochecer | 0 falsos positivos | 0 falsos positivos en 1 711 frames |

El único retroceso es en bates (1.4%), menor frente a la ganancia en blur, oclusión y
desenfoque. Mismo hash verificado en `app/models/best.pt` y dentro de las imágenes
`tesis-backend:local` y `sentinel-agent:local`.

Evaluación: `cola_noche/evaluar_todo.py` y `cola_noche/evaluar_yolov5.py`; resultados en
`salida_noche/evaluacion_parcial_sin_v5.json`, `evaluacion_yolov5s.json` y
`benchmark_latencia.json`.

#### Faster R-CNN (detector de dos etapas, también pedido por el revisor)

`experimentos/faster_rcnn/`: torchvision `fasterrcnn_resnet50_fpn_v2` desde pesos COCO,
mismos datos de entrenamiento, lado mayor 640 px, 20 épocas, semilla 0; aumento solo con
volteo horizontal (el estándar de este detector). 20 épocas en ~16 h en la RTX 2070,
retomado tras un corte de luz desde el checkpoint de la época 7. Como torchvision y
Ultralytics evalúan distinto, se reimplementó el evaluador de Ultralytics y se aplicó a
todos; reproduce las cifras YOLO con ±0.005 de mAP50 en limpio.

| Modelo (evaluador común) | P | R | mAP50 | mAP50-95 | GPU P50 | CPU P50 |
|---|---|---|---|---|---|---|
| **Faster R-CNN** | 0.888 | 0.780 | **0.864** | 0.532 | 71.4 ms | 2 040 ms |
| v5 (desplegado) | 0.883 | 0.782 | 0.857 | 0.532 | 13.4 ms | 124 ms |
| YOLOv8s (COCO) | 0.870 | 0.766 | 0.849 | 0.513 | 14.0 ms | 124 ms |

Robustez de Faster R-CNN (mAP50): compresión 0.776, blur 0.541, oclusión 0.365,
desenfoque 0.657, **baja luz 0.668 (el mejor de todos)**, elevada 0.776, lateral 0.811.

**Lectura:** Faster R-CNN gana menos de 1 punto de mAP50 y es el mejor con poca luz, pero
es ~5× más lento en GPU y ~16× en CPU: a 71 ms por imagen una GPU analiza ~14 fps en
total, frente a 16 cámaras × 5.9 fps del agente con YOLOv8s. Confirma la elección de un
detector de una etapa para tiempo real con varias cámaras. Resultados en
`docs/evidencia_externa/comparacion/evaluacion_faster_rcnn.json`.

#### Versión anterior de esta comparación (reemplazada)
Se entrenó YOLOv5s (paquete oficial `yolov5`, no `yolov5u` que en realidad es
arquitectura YOLOv8) desde pesos COCO preentrenados, mismo dataset combinado y mismo
protocolo que v4 (20 épocas, batch 16, imgsz 640, mismo RTX 2070). Evaluados ambos en
el mismo test externo de Zenodo nunca visto en entrenamiento, en el mismo hardware:

| Métrica | v4 (YOLOv8s) | YOLOv5s |
|---|---|---|
| Precision | **0.890** | 0.845 |
| Recall | 0.800 | **0.816** |
| mAP50 | **0.878** | 0.864 |
| mAP50-95 | **0.584** | 0.514 |
| Inferencia (ms/img, misma GPU) | 5.0 | **3.6** |

**Lectura honesta:** son muy cercanos en mAP50 (diferencia de 1.4 puntos), con
YOLOv8s ligeramente mejor en precisión y mAP50-95, y YOLOv5s con mejor recall y
notablemente más rápido (28% menos latencia de inferencia). Para una aplicación de
seguridad donde omitir un arma real pesa más que una falsa alarma, el recall más
alto de YOLOv5s es relevante y vale la pena discutirlo, no solo citar el mAP50.

**Salvedad metodológica a declarar en el manuscrito:** v4 partió de v3 (ya
preentrenado en este dominio específico), mientras que YOLOv5s partió de pesos COCO
genéricos — no es una comparación de arquitectura pura en igualdad de condiciones de
inicialización, sino "mejor punto de partida disponible para cada uno" bajo el mismo
presupuesto de épocas/datos. Es una comparación realista (así se usaría en la
práctica) pero hay que decirlo explícitamente para que no parezca que se ocultó.

Script: `dataset_externo_zenodo/entrenar_yolov5.sh`, pesos en
`dataset_externo_zenodo/salida_yolov5/yolov5s_comparacion/weights/best.pt`. No se
desplegó (sigue v4 en producción) — esto es solo para la comparación del paper.

### 4. Medir latencia end-to-end y throughput — ⚠️ Parcial (instrumentación lista, falta correrla)
Se añadió medición real con `time.monotonic()` en las cuatro etapas:

- `sentinel_agent.py`: `inferencia_ms` (captura→inferencia) y `preproc_ms`
  (dibujar evidencia + redimensionar + codificar JPEG), más `red_ms` (ida y
  vuelta HTTP) — se imprime una línea `LATENCIA cam=... ...` por cada alerta.
- `app/routers/agent.py`: `latencia_backend_ms` (recepción→persistencia→
  WebSocket) y `latencia_agente_a_backend_ms` (aprox. por reloj de pared,
  requiere NTP entre equipos) — logger `sentinel.latency`, nivel INFO.
- `app/scripts/calcular_latencia.py`: agrega un log del backend en P50/P95 por
  etapa.

**Resuelto hoy.** Se conectó el agente real contra la cámara RTSP de la
municipalidad (misma red local, credenciales en `.env` del agente), con
detecciones apuntando a un backend de prueba local (no a producción). Se agregó
además `LATENCIA_FRAME` — faltaba medir la latencia de **cada** frame, no solo
los que disparan alerta (en la cámara real no hubo armas visibles durante la
prueba, así que sin ese log no habría datos).

**Latencia de inferencia por frame, cámara real, CPU (sin GPU — así corre en
producción, junto a las cámaras), 664 frames / ~3.25 min:**

| Percentil | Latencia |
|---|---|
| P50 | 87.6 ms |
| P95 | 118.1 ms |
| P99 | 154.3 ms |
| Media | 93.2 ms |

Throughput efectivo ~3.4 FPS. Un solo outlier (1534 ms) correspondiente al
primer frame (carga del modelo en memoria) — no representativo del régimen
estable, conviene excluirlo o reportarlo aparte como "warmup". Sin
reconexiones ni frames perdidos en todo el período.

Hardware: RTSP vía red local de la municipalidad, agente en contenedor Docker
(`sentinel-agent:local`, Python 3.10, Ultralytics 8.3.40), CPU del host
(sin GPU asignada al contenedor — representa fielmente el despliegue real).

### 5. Carga con múltiples cámaras — ✅ Resuelto: 16 cámaras con el agente multicámara

**Versión final (reemplaza las conclusiones de las tablas de más abajo).** La
limitación encontrada —un contenedor por cámara, cada uno con su propia copia del
modelo— se resolvió con un rediseño del agente (`agente/sentinel_agent.py`): **un solo
proceso** atiende todas las cámaras de `CAMARAS`; un hilo por cámara lee el video y
conserva solo el frame más reciente (además vacía el búfer RTSP, así se analiza lo
último), y el modelo, cargado una vez, infiere los frames nuevos de todas en un lote. Las
alertas se envían en paralelo y la espera entre alertas es por cámara. Con una sola
cámara (`RTSP_URL`) funciona como antes. Prueba: `prueba_carga_multi.sh`, mismo video y
hardware que las tablas de abajo.

| Cámaras | Modo | FPS/cámara | Inferencia P50 / P95 | CPU total | RAM total |
|---|---|---|---|---|---|
| 1 | GPU | 5.81 | 40 / 43 ms | 21% | 1.0 GB |
| 4 | GPU | 5.92 | 83 / 102 ms | 52% | 1.1 GB |
| 8 | GPU | 5.88 | 97 / 115 ms | 65% | 1.3 GB |
| **16** | **GPU** | **5.86** | **121 / 154 ms** | **97%** | **1.5 GB** |
| 1 | CPU | 5.93 | 114 / 135 ms | 430% | 0.5 GB |
| 4 | CPU | 3.20 | 373 / 417 ms | 779% | 0.8 GB |
| 8 | CPU | 1.55 | 766 / 822 ms | 739% | 1.0 GB |
| 16 | CPU | 0.75 | 1.54 / 1.66 s | 742% | 1.5 GB |

La inferencia reportada es la del lote completo (lo que espera cada frame).

- **Con GPU, 16 cámaras a ~5.9 FPS cada una**, P95 de 154 ms y 1.5 GB de RAM en total
  (antes 16 no cabían en memoria; 8 ocupaban 6.5 GB). Durante la prueba de 16 cámaras se
  enviaron 266 alertas al backend sin errores.
- **Solo CPU mejora entre 5× y 9×** frente a un proceso por cámara (4 cámaras: 0.61 →
  3.2 FPS, 2.2 s → 0.37 s); el límite práctico en CPU es ~4 cámaras.
- Con una cámara, incluso en CPU sube de 3.9 a 5.9 FPS: leer el video en su propio hilo
  separa la decodificación de la inferencia.

#### Primera ronda (arquitectura anterior, un contenedor por cámara)

Se simularon 1, 4, 8 y 16 cámaras con contenedores `sentinel-agent:local` independientes
alimentados por un video sintético (no la cámara RTSP real, para no arriesgar saturar el
único stream físico disponible — ver nota de #4), apuntando a un backend de prueba
local. CPU: host con 12 núcleos, sin GPU asignada a los contenedores (igual que el
despliegue real del agente).

| Flujos | FPS/stream | Inferencia P50 | Inferencia P95 | RAM/contenedor |
|---|---|---|---|---|
| 1 | 3.59 | 91.7 ms | 123.0 ms | 521 MiB |
| 4 | 0.86 | 1.42 s | 1.78 s | 535 MiB |
| 8 | 0.29 | 4.11 s | 4.96 s | 535 MiB |
| 16 | 0.15 | 8.26 s | **85.1 s** | 387 MiB |

**Conclusión honesta — hay que declararla como limitación en el manuscrito, no
suavizarla:** el despliegue actual (CPU, un contenedor por cámara, sin GPU en el
agente) **no escala más allá de 1-2 cámaras simultáneas** en un host de 12 núcleos.
Desde 4 streams la latencia ya es inaceptable para alertas en tiempo real (>1s), y en
16 streams el P95 llega a 85 segundos — inviable operativamente. A los 16 streams
además se observó alta varianza entre instancias: una cámara quedó fuertemente
desfavorecida por el scheduler del SO (1 solo frame procesado en toda la ventana de
prueba, con esa inferencia tardando 19s por inanición de CPU), mientras otras
procesaron 13-15 frames.

**Esto no es un fallo del experimento, es el resultado real.** El sistema necesitaría
GPU en el agente o un agente por cada 1-2 cámaras como mucho (horizontal, no vertical)
para cumplir con cargas de 4+ cámaras en tiempo real. Vale la pena proponerlo
explícitamente como trabajo futuro en la respuesta al reviewer, en vez de presentar
el sistema como listo para 16 cámaras sin esta evidencia.

Script: `dataset_externo_zenodo/prueba_carga.sh`. Datos crudos en
`dataset_externo_zenodo/resultados_carga/`.

#### Segunda ronda: versiones fijadas, hilos limitados y GPU

La tabla anterior se midió con el agente sin versiones fijas (ultralytics 8.4.183,
torch 2.14 — cada build instalaba lo último). Se fijaron las versiones del agente
(`requirements.txt`: ultralytics 8.3.40, torch 2.8.0+cu128, opencv-python 5.0.0.93, numpy
2.0.2, Python 3.10) y se repitió todo. Laptop: 6 núcleos físicos / 12 lógicos, RTX 2070
8 GB, Docker Desktop con VM de 7.6 GB de RAM. Inferencia P50/P95 por frame, descartando
el primer frame de cada cámara:

| Modo | Cámaras | FPS/cámara | Inferencia P50 | Inferencia P95 | CPU total | RAM/cámara |
|---|---|---|---|---|---|---|
| CPU | 1 | 3.85 | 101 ms | 147 ms | 286% | 477 MiB |
| CPU | 4 | 0.61 | 2.23 s | 2.64 s | 1173% | 485 MiB |
| CPU | 8 | 0.19 | 5.87 s | 6.85 s | 1221% | 478 MiB |
| CPU | 16 | 0.08 | 12.9 s | 15.2 s | 1174% | 395 MiB |
| CPU, hilos limitados | 4 | 0.59 | 2.29 s | 2.54 s | 1156% | 475 MiB |
| CPU, hilos limitados | 16 | 0.09 | 12.6 s | 14.2 s | 1171% | 408 MiB |
| **GPU** | 1 | 4.85 | **40 ms** | 45 ms | 18% | 995 MiB |
| **GPU** | 4 | 5.14 | **27 ms** | 166 ms | 61% | 986 MiB |
| **GPU** | 8 | 5.27 | **33 ms** | 80 ms | 137% | 814 MiB |
| GPU | 16 | — | — | — | — | — |

- **Con GPU el sistema escala a 8 cámaras** al máximo de diseño (~5 FPS/cámara) con
  P95 < 170 ms y la CPU casi libre.
- **16 cámaras con GPU fallaron por memoria, no por cómputo**: cada cámara es un proceso
  propio con su contexto CUDA y su copia del modelo (~0.8-1 GB de RAM c/u); 16 superan
  los 7.6 GB de la VM de Docker y el sistema mató contenedores (código 137). Es un límite
  de la arquitectura un-proceso-por-cámara. Solución propuesta: un solo proceso que
  atienda varias cámaras con el modelo compartido (y procesamiento por lotes).
- **Limitar hilos no ayudó.** Se verificó que el límite sí se aplica a torch (1 hilo vs.
  6 por defecto), pero OpenCV mantiene su propio pool de 12 hilos, y la laptop tiene solo
  6 núcleos físicos.
- **Solo CPU: 1 cámara en tiempo real** en esta laptop. Queda pendiente repetirlo en el
  servidor del autor con más núcleos (mismo script, modo `cpu` / `hilos` / `gpu`).
- **Frame skipping por diseño:** el bucle del agente tiene `time.sleep(0.2)` en cada
  iteración y el buffer RTSP en 1 frame, así que procesa como máximo ~5 FPS por cámara y
  descarta el resto de frames de la cámara. No estaba documentado; el reviewer pide
  explícitamente la estrategia de frame skipping.

### 6. Robustez en condiciones adversas — ✅ Resuelto

**Falsos positivos reales (commit `cb691a2`):** motos confundidas con arma de fuego
al 70-77 % de confianza sostenida en video real de calle → corregido a 0/60 falsos
positivos con el ajuste fino (v3).

**Baja luz, cámara real, de noche (misma cámara de la calle):** en dos sesiones
nocturnas, **3082 frames procesados, 0 falsos positivos** sobre motos, carros y
personas reales — el fix de v3/v4 aguanta también de noche.

Latencia nocturna medida limpia (agente solo, configuración de producción):
**P50 = 97.6 ms, P95 = 131.4 ms**. *Corrección:* una versión anterior de este
documento reportaba P95 = 218.5 ms y lo atribuía al jitter de red. Las dos cosas
estaban mal: ese P95 es solo de inferencia (no incluye la lectura del stream), y
la causa real fue que en ese momento corrían en la misma máquina la generación y
evaluación de las degradaciones, compitiendo por la CPU. Medición descartada.

**Red / RTSP (cámara real, de noche, 4 configuraciones × 2 min, `prueba_red.sh`):**

| Configuración | Lectura P50 | Lectura P95 | Inferencia P50 | Inferencia P95 | FPS |
|---|---|---|---|---|---|
| UDP, stream principal 1080p (producción) | 3.1 ms | 6.7 ms | 97.6 ms | 131.4 ms | 3.54 |
| TCP, stream principal | 2.7 ms | 4.7 ms | 98.0 ms | 126.0 ms | 3.60 |
| UDP, substream | 1.4 ms | 1.8 ms | 111.8 ms | 141.4 ms | 3.38 |
| TCP, substream | 1.1 ms | 1.8 ms | 113.7 ms | 152.1 ms | 3.35 |

- **La red no es el cuello de botella**: obtener un frame cuesta ≤7 ms en P95 frente
  a ~100-150 ms de inferencia. No se recomienda ningún cambio de transporte.
- **El substream no conviene**: lee más rápido pero infiere más lento — es 4:3 y al
  reescalarlo a 640 px deja más píxeles que el 16:9 del principal — y degradaría la
  evidencia enviada al operador.
- No se pudo confirmar que la opción TCP (`OPENCV_FFMPEG_CAPTURE_OPTIONS`) se aplicara
  efectivamente: aparecen 4 avisos `bad cseq`, que no deberían existir sobre TCP. No
  altera la conclusión. **No se versiona la captura real** (siguiendo la misma
política del proyecto: "las evidencias no se versionan, son fotogramas reales de la
vía pública con personas identificables" — ver README); queda solo en disco local
(`dataset_externo_zenodo/noche_captura.jpg`) para consulta, nunca en GitHub.

> **Reemplazada:** la tabla siguiente se midió sobre el test con 194 duplicados y con
> conf=0.25. Las cifras válidas, sin duplicados y para todos los modelos (más
> desenfoque y baja luz), están en el punto 3. Sin duplicados las degradaciones pegan
> más fuerte (blur de v4: 0.468 en vez de 0.583): las fotos duplicadas el modelo las
> reconocía aun degradadas.

**Motion blur, compresión y oclusión (dataset externo, v4, conf=0.25):**

| Condición | Precision | Recall | mAP50 |
|---|---|---|---|
| Base (sin degradar) | 0.890 | 0.800 | 0.878 |
| Compresión JPEG agresiva (q=10) | 0.867 | 0.728 | 0.829 |
| Motion blur (kernel 25px) | 0.760 | 0.375 | **0.583** |
| Oclusión parcial (40% de la caja) | 0.426 | 0.283 | **0.307** |

**Lectura honesta:** el modelo tolera razonablemente bien la compresión agresiva
(pérdida de ~5 puntos de mAP50), pero **se degrada fuerte con desenfoque y oclusión**
— con oclusión del 40% el mAP50 cae a 0.307, prácticamente al nivel del modelo sin
ajuste externo (v3). Esto es consistente con el falso negativo real ya documentado en
el punto 2 (cuchillo perdido por blur + oclusión simultáneos) — no es un hallazgo
aislado, es un patrón.

**Curva precision-recall** (pedida explícitamente por el reviewer) en
`docs/evidencia_externa/PR_curve.png`, generada sobre el test externo limpio.

Scripts: `dataset_externo_zenodo/generar_degradaciones.py`,
`dataset_externo_zenodo/evaluar_degradaciones.py`.

**Recomendación para el manuscrito:** declarar esto como limitación conocida y
proponer como trabajo futuro incorporar ejemplos con blur/oclusión al entrenamiento
(augmentation), ya que hoy el modelo nunca los vio durante el ajuste fino. *(Hecho
después: es v5, ver punto 3.)*

#### Ángulo de cámara (simulado)

El revisor pide también "varied camera angles". `generar_angulos.py` deforma el test sin
duplicados con una perspectiva fija: cámara **elevada** (borde superior angostado 20% por
lado, alto al 80%) y cámara **lateral** (un borde vertical acortado 20% en cada extremo,
ancho al 80%). Las cajas pasan al rectángulo que contiene sus esquinas proyectadas.
Ningún entrenamiento usó estas deformaciones (`evaluar_angulos.py`,
`evaluar_angulos_yolov5.py`; resultados en `docs/evidencia_externa/comparacion/`):

| Modelo | Limpio | Elevada | Lateral |
|---|---|---|---|
| v3 | 0.334 | 0.265 | 0.288 |
| YOLOv8n | 0.795 | 0.717 | 0.739 |
| YOLOv5s | 0.838 | **0.792** | **0.800** |
| YOLOv8s | 0.854 | 0.774 | 0.802 |
| v4 | 0.847 | 0.755 | 0.791 |
| **v5** | **0.859** | 0.777 | 0.798 |

Todos pierden entre ~4 y 9 puntos; YOLOv5s es el que menos pierde en vista elevada. Es una
simulación geométrica: ángulos reales quedan como limitación.

#### Puntos de operación a nivel de imagen (v5, test externo sin duplicados)

El revisor pide "operating points for different use cases". La métrica por cajas cuenta
como error un arma detectada con la caja desplazada; en operación lo que importa es si
la imagen dispara alerta. Para cada umbral (`puntos_operacion.py`), sobre 768 imágenes
con arma y 286 sin arma:

| Umbral | Imágenes con arma que alertan | Falsas alarmas en imágenes sin arma | Uso sugerido |
|---|---|---|---|
| 0.25 | 89.6% | 8.0% | — |
| 0.40 | 84.8% | 4.9% | — |
| 0.50 | 81.5% | 3.2% | Alta seguridad: prioriza no perder armas |
| 0.60 | 75.3% | 1.75% | — |
| **0.65 (producción)** | **70.4%** | **1.05%** | Equilibrio |
| 0.70 | 64.8% | 0% | Mínimo ruido |
| 0.80 | 44.8% | 0% | — |

Al umbral de producción, por clase: arma de fuego 74.4%, arma blanca 67.5% (v4: 71.9% y
64.1%, falsa alarma 0.35%).

- Es por **frame aislado**: en video un arma visible varios segundos tiene ~5
  oportunidades por segundo, así que la tasa por evento debe ser mayor (no medible con
  fotos sueltas; queda como trabajo futuro con video anotado).
- Las imágenes sin arma de este test son difíciles a propósito (incluyen personas con
  bates). En la calle real, al umbral 0.65, hubo 0 falsas alarmas en ~4 800 frames.
- Se mantiene 0.65 en producción. El umbral se cambia en vivo desde el panel; esta tabla
  es la guía para elegirlo según el contexto.
- Mirando los casos uno por uno, de los 6 primeros falsos positivos del test, 5 eran el
  arma correcta con la caja desplazada respecto de la anotación y solo 1 un error real
  (un bate). Evidencia y casos clasificados en `docs/evidencia_externa/v5/`.

---

## PRIORIDAD 2 — ALTA

### 7. Origen, versiones y licencias de datos — ⚠️ Parcial (falta confirmar enlaces)
`metodologia_particion.md` documenta tamaños, particiones y distribución de clases,
pero no incluye enlaces/licencias exactas de Kaggle/DatasetNinja.

**Distribución por fuente reconstruida** (`distribucion_fuentes.sh`, sobre
`dataset_80_20` completo, agrupando por prefijo del nombre de archivo; todos los
archivos tienen el sufijo `.rf.` de export de Roboflow):

| Prefijo | arma_fuego | arma_blanca | fondo | Origen probable (por confirmar) |
|---|---|---|---|---|
| `armas` | 8 939 | 4 | — | Dataset de pistolas U. de Granada (Olmos et al.), archivos "armas (N)" |
| `pistol` | 6 814 | — | — | Dataset "Pistols" (Kaggle/DatasetNinja) |
| `knife` | — | 4 699 | — | Dataset de cuchillos |
| fechas `2022101x` | — | 1 346 | — | Cuchillos, fotos fechadas |
| `CAR`, `CA`, `test` | 2 055 | — | — | Sin identificar |
| `KravMaga…`, `DefenseKnife…`, etc. | — | ~950 | — | Frames de videos de defensa personal |
| `open`, `opencv`, `DSC`, `pisau`, ~600 nombres aleatorios | — | ~1 750 | — | Varias fuentes de cuchillos ("pisau" = cuchillo en indonesio) |
| `Robbery`, `Arrest` | 44 | — | — | Frames de **UCF-Crime** |
| `fondo`, `1…` | — | — | 2 091 | Fondos generados + capturas de la calle real |

El total de `arma_fuego` (17 852) cuadra exactamente con `metodologia_particion.md`.

**Pendiente del autor:**
- Enlaces exactos y licencias de cada dataset descargado (solo se pueden inferir por
  los nombres; no hay registro de descarga en el disco).
- **UCF-Crime** tiene licencia restringida a investigación: verificar si sus frames
  pueden redistribuirse o si hay que excluirlos de la declaración de disponibilidad
  (afecta el punto 17).
- Los 4 objetos `arma_blanca` dentro del prefijo `armas` (pistolas): **revisados uno por
  uno, el cuchillo está bien anotado; lo que falta es la caja de la pistola visible**
  (anotación incompleta). Ver `docs/anotacion/`, que documenta además el protocolo
  usado y una guía para anotar datos nuevos (punto 8).

### 8. Anotación y augmentations — ⚠️ Parcial (hallazgo: fuga train/val por aumentos)
Las reglas de generación de fondos están documentadas (recorte de regiones sin cajas,
descarte por baja varianza). Falta documentar parámetros de Roboflow/augmentation del
dataset original y concordancia entre anotadores (si existiera más de uno).

**Hallazgo — copias aumentadas de Roboflow repartidas entre train y val.** Roboflow
exporta varias versiones aumentadas de cada foto original con el mismo nombre base y
distinto sufijo `.rf.<hash>`. El dataset se re-partió después al azar por archivo, no
por foto original:

| | Imágenes | Fotos originales únicas |
|---|---|---|
| train | 21 534 | 12 834 |
| val | 5 386 | 4 702 |
| **originales con copias en train Y en val** | | **3 056 (65% de los de val)** |

Copias por original en train: 7 117 con 1, 2 869 con 2, 2 747 con 3, 101 con 4-6.

`metodologia_particion.md` afirma que "se verificó la ausencia de solapamiento entre
subconjuntos", pero la verificación fue por nombre exacto de archivo, que difiere entre
copias. **Consecuencia:** todas las métricas de validación interna (0.957 de v2, 0.944
de v4) están infladas y no deben citarse como evidencia de generalización — es la
explicación más probable de la brecha con el test externo. Las cifras externas (Zenodo)
no se ven afectadas por esto.

**Corrección recomendada para futuros entrenamientos:** partir por foto original
(agrupando por el nombre antes de `.rf.`), no por archivo.

### 9. README reproducible — ✅ Resuelto
`README.md` cubre instalación, Docker, variables de entorno, arquitectura y decisiones
de diseño. Se agregó `experimentos/` con todos los scripts que producen las cifras de
este documento y un `experimentos/README.md` con versiones exactas, semillas, montajes
de Docker y el orden de ejecución.

**Versiones fijadas.** Ni el backend ni el agente fijaban torch: el agente, al
reconstruirse, había instalado ultralytics 8.4.183 y torch 2.14 (CUDA 13, incompatible
con el driver de la laptop), distinto del backend. Se fijaron en ambos
`requirements.txt` las versiones con que se midió todo: ultralytics 8.3.40, torch 2.8.0,
torchvision 0.23.0, numpy 2.0.2.

El agente ya está versionado en `agente/` (ver nota al final). **Demo:** `demo/` levanta Mongo,
backend y agente con un video de ejemplo de 30 s (CC BY) en un solo comando; probada desde
cero: genera alertas e incidentes en menos de un minuto.

### 10. Código, pruebas y automatización — ✅ Resuelto
Ya existían `tests/test_autenticacion.py`, `tests/test_agente.py`,
`tests/test_regresiones.py` (contra sistema real, no mocks) — bien documentados y con
intención clara. Se añadió `.github/workflows/tests.yml`: levanta MongoDB como
servicio, arranca el backend real con uvicorn, espera a que responda y corre
`pytest tests/ -v` en cada push/PR. No se pudo verificar en GitHub Actions desde aquí
(hay que hacer push); revisar el primer run por si hace falta ajustar timeouts.

### 11. Privacidad y protección operativa — ⚠️ Parcial (mecanismo listo, falta el plazo)
Ya implementado en código: credenciales RTSP cifradas con Fernet (`app/core/crypto.py`),
el sistema nunca actúa solo — crea alertas para que un operador decida (diseño
human-in-the-loop).

**Retención de evidencia implementada** (`app/services/retention_service.py`): con
`EVIDENCE_RETENTION_DAYS` > 0, el backend borra cada hora las imágenes con más de esos
días — en el incidente, en la alerta y los archivos en disco — y **conserva el registro
del incidente** (fecha, cámara, tipo, confianza) con un sello `evidence_purged_at`. Por
defecto vale 0 (sin purga) hasta que la institución fije el plazo.
Prueba: `tests/test_retencion.py`, sobre una base de datos desechable.

**Falta:** el plazo en días (decisión institucional), y la documentación formal de
minimización de datos y de las aprobaciones necesarias para el despliegue.

### 12. Matriz de confusión normalizada — ✅ Resuelto (falta trasladar al texto)
`metodologia_particion.md` ya tiene la tabla de calibración de confianza (92,3 % de
acierto global, >97 % sobre 0.60) que explica el comportamiento del modelo por rango de
confianza. Falta explicar específicamente el eje de normalización de la matriz de
confusión y los valores 0.54/0.46 del fondo que señala el Reviewer 4.

### 13. Referencias bibliográficas — ❌ Pendiente
Vive en el manuscrito, que no está disponible en este entorno.

---

## PRIORIDAD 3 — FINAL (todo vive en el manuscrito)

### 14. Figuras y tablas — ❌ Pendiente (necesita el manuscrito)
### 15. Errores del PDF del revisor — ✅ Resuelto (salvo referencias, en Mendeley)
Las 22 marcas del PDF del Reviewer 4: palabras clave (3), espacios tras citas (2), figuras
sin número o referencia (9), 100 vs. 20 épocas (1), eje de la matriz de confusión (1),
punto final en la declaración de ética (1, reescrita), contribución de Wilder Marlo
Rimarachin (1, falta el texto del autor) y referencias (4: quitar "Dr.", títulos en
mayúsculas, un solo formato; se corrigen en Mendeley). El PDF no se versiona: es parte de
la revisión confidencial.
### 16. Declaraciones éticas AIRA — ❌ Pendiente (necesita el manuscrito/formulario AIRA)
### 17. Disponibilidad de datos y materiales — ⚠️ Parcial
El código está público en GitHub (`BREYNERCITO777/BACKEND_PROYECTO_TESIS`). Falta
confirmar si el dataset (Kaggle/DatasetNinja) tiene URLs públicas estables y licencias
claras para citar en la declaración de disponibilidad.
### 18. Respuesta punto por punto — ❌ Pendiente (depende de que se cierren los puntos anteriores)

---

## Incidente durante esta sesión (corregido)

Un build de Docker que se había lanzado antes de descubrir que v3 era el modelo
correcto terminó en segundo plano **después** de la corrección, y sobrescribió la
imagen `tesis-backend:local` con el modelo v2 (el del bug de falsos positivos con
motos) y con el código desactualizado de `BACKEND_PROYECTO_TESIS-main`. Se detectó
al verificar el hash del modelo dentro de la imagen y se corrigió reconstruyendo
`tesis-backend:local` desde `repo-github` (código correcto + modelo v3). Verificado:
hash del modelo dentro de la imagen final = `1698820f...` (v3, correcto).

**Nota para la próxima vez:** el contenedor `tesis-backend` sigue detenido (no se
reinició tras el rebuild). Si se reinicia desde Docker Desktop, confirmar que toma la
imagen nueva (`docker inspect tesis-backend --format '{{.Image}}'` debe coincidir con
el ID de la imagen reconstruida).

## Nota sobre `sentinel-agent`

**Resuelto:** el agente vive ahora en `agente/` dentro de este repositorio, con sus
versiones fijadas y la instrumentación de latencia. Se construye desde la raíz y copia
`app/models/best.pt`, así que agente y backend no pueden volver a quedar con modelos
distintos (el problema encontrado el primer día). Al pasarlo se descubrió que el pin
`opencv-python==5.0.0` no existía en pip (es `5.0.0.93`): cualquier build desde cero
fallaba. Corregido. La copia vieja en `BACKEND_PROYECTO_TESIS-main/sentinel-agent` queda
solo como respaldo.

## Resumen de prioridad inmediata

1. ~~Decisión urgente sobre #2~~ **Resuelto**: v4 desplegado, sin regresiones. Su
   mAP50 externo de 0.878 está **inflado** por 194 duplicados dentro de Zenodo; la
   cifra válida sale de la re-evaluación sobre las 1 054 imágenes sin duplicados
   (en curso en la cola nocturna).
2. ~~#3 (YOLOv5)~~ **Resuelto**: YOLOv8s (v4) y YOLOv5s quedan muy cerca en mAP50
   (0.878 vs 0.864); YOLOv5s gana en recall y velocidad. Sigue v4 en producción.
3. ~~#4 y #5~~ **Resueltos**: latencia real medida contra la cámara de la calle
   (P50 87.6ms, P95 118.1ms, CPU) y carga 1/4/8/16 streams simulados. Resultado:
   **solo CPU soporta 1 cámara en tiempo real; con GPU, 8 cámaras a ~5 FPS c/u
   (P95 < 170 ms)**. 16 cámaras fallan por memoria (un proceso por cámara), no por
   cómputo — se propone un proceso multicámara con modelo compartido.
4. **#13-18** dependen de tener el manuscrito a mano.
5. **#11** (retención de datos) es una decisión institucional, no de código — conviene
   consultarlo con el asesor o la municipalidad antes del 30 de octubre.
6. **Prioridad 1 (crítica) completa al 100%**: #1, #2, #3, #4, #5 y #6 tienen
   evidencia real, reproducible y, cuando el resultado fue malo (escalado a 16
   cámaras, oclusión/blur), se declaró así en vez de maquillarlo.
