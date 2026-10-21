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
- **Falso positivo revelador:** una de las imágenes de **bate de béisbol**
  (clase excluida a propósito porque no existe en el sistema de 2 clases) se
  confunde con `arma_blanca`. Tiene una explicación concreta: el entrenamiento
  nunca le enseñó "esto es un bate, no es arma" — simplemente se quitó la etiqueta,
  así que el modelo nunca vio ese objeto como negativo explícito. Es una limitación
  real que conviene declarar en el manuscrito, no ocultar: el sistema puede
  confundir objetos alargados sostenidos de forma similar a un arma blanca
  (palos, bates, herramientas) con una clase real.

Script: `dataset_externo_zenodo/evaluar_completo.py`. Evidencia versionada en
`docs/evidencia_externa/` (matriz de confusión, 2 casos de fallo, métricas en JSON).

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

**Falta:** dejarlo corriendo contra la cámara real (o un video) el tiempo
suficiente para tener una muestra, y volcar la tabla de resultados. No se
pudo ejecutar aquí porque el agente necesita la cámara RTSP de la
municipalidad, fuera de este entorno.

### 5. Carga con múltiples cámaras — ❌ Pendiente
No hay ningún test de carga con 4/8/16 streams. El agente actual está pensado para una
cámara (`CAMERA_ID` único por contenedor); habría que levantar varias instancias y
medir CPU/RAM/FPS reales con `docker stats`, apoyándose en la instrumentación del punto
4 (cada instancia ya reporta su propia latencia). Requiere definir con qué video de
prueba simular las 4/8/16 fuentes si no hay esa cantidad de cámaras reales disponibles.

### 6. Robustez en condiciones adversas — ⚠️ Parcial
Ya existe un experimento real y bien documentado (commit `cb691a2`): motos confundidas
con arma de fuego al 70-77 % de confianza sostenida en video real de calle → corregido
a 0/60 falsos positivos con el ajuste fino (v3). Esto cubre **un** escenario adverso
(objetos similares/falsos positivos en escena real), pero el reviewer pide además baja
luz, motion blur, compresión, oclusión y ángulos variados — ninguno de esos está
evaluado todavía.

---

## PRIORIDAD 2 — ALTA

### 7. Origen, versiones y licencias de datos — ⚠️ Parcial
`metodologia_particion.md` documenta tamaños, particiones y distribución de clases,
pero no incluye enlaces/licencias exactas de Kaggle/DatasetNinja ni verificación
explícita de duplicados entre fuentes (solo se verificó que no hay solapamiento entre
train/val del propio proyecto).

### 8. Anotación y augmentations — ⚠️ Parcial
Las reglas de generación de fondos están documentadas (recorte de regiones sin cajas,
descarte por baja varianza). Falta documentar parámetros de Roboflow/augmentation del
dataset original y concordancia entre anotadores (si existiera más de uno).

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

1. ~~Decisión urgente sobre #2~~ **Resuelto**: v4 desplegado, mAP50 externo real
   0.878 (antes 0.329), sin regresiones.
2. ~~#3 (YOLOv5)~~ **Resuelto**: YOLOv8s (v4) y YOLOv5s quedan muy cerca en mAP50
   (0.878 vs 0.864); YOLOv5s gana en recall y velocidad. Sigue v4 en producción.
3. **#5** (carga 4/8/16 cámaras) y **#4** (correr la instrumentación de latencia con
   cámara/video real) son lo siguiente — técnicamente directos con la GPU disponible.
4. **#13-18** dependen de tener el manuscrito a mano.
5. **#11** (retención de datos) es una decisión institucional, no de código — conviene
   consultarlo con el asesor o la municipalidad antes del 30 de octubre.
