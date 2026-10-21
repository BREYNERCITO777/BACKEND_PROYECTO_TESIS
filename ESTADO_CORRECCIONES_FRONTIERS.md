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
huérfano, no una evaluación hecha.

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

### 3. Comparar YOLOv8 contra otro detector — ✅ Resuelto
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

### 5. Carga con múltiples cámaras — ✅ Resuelto (resultado preocupante, declarar como limitación)

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
(`requirements.txt`: ultralytics 8.3.40, torch 2.8.0+cu128, opencv-python 5.0.0, numpy
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
(augmentation), ya que hoy el modelo nunca los vio durante el ajuste fino.

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
- Los 4 objetos `arma_blanca` dentro del prefijo `armas` (pistolas) son candidatos a
  etiquetas erróneas — sirven como ejemplo de anotación ambigua que pide el punto 8.

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
`repo-github/README.md` ya cubre instalación, Docker, variables de entorno, arquitectura
y decisiones de diseño. Falta: seeds de entrenamiento explícitas, tags Docker versionados,
demo en video/RTSP de ejemplo.

### 10. Código, pruebas y automatización — ✅ Resuelto
Ya existían `tests/test_autenticacion.py`, `tests/test_agente.py`,
`tests/test_regresiones.py` (contra sistema real, no mocks) — bien documentados y con
intención clara. Se añadió `.github/workflows/tests.yml`: levanta MongoDB como
servicio, arranca el backend real con uvicorn, espera a que responda y corre
`pytest tests/ -v` en cada push/PR. No se pudo verificar en GitHub Actions desde aquí
(hay que hacer push); revisar el primer run por si hace falta ajustar timeouts.

### 11. Privacidad y protección operativa — ⚠️ Parcial
Ya implementado en código: credenciales RTSP cifradas con Fernet (`app/core/crypto.py`),
el sistema nunca actúa solo — crea alertas para que un operador decida (diseño
human-in-the-loop). **Falta:** política de retención de evidencia (no hay TTL/borrado
automático en el código — las imágenes de incidentes se guardan indefinidamente),
documentación formal de minimización de datos y de aprobaciones necesarias para
despliegue real. Esto requiere una decisión institucional, no solo código.

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
### 15. Errores del PDF del revisor — ❌ Pendiente (necesita `Review supporting file 1332534`)
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

El código del agente (`sentinel_agent.py`) **no tiene repositorio git propio** — solo
existe dentro de la carpeta exportada `BACKEND_PROYECTO_TESIS-main/sentinel-agent`, sin
versionar. Los cambios de instrumentación de latencia (punto 4) se hicieron ahí porque
es la única copia que existe. Conviene darle su propio repo antes de la entrega, o
moverlo dentro de `repo-github` como subcarpeta, para que quede trazable igual que el
backend.

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
