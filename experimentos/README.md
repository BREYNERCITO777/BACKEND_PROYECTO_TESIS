# Experimentos de la revisión de Frontiers

Scripts que producen todas las cifras de `ESTADO_CORRECCIONES_FRONTIERS.md`. Están en
el orden en que hay que correrlos. Cada script dice en su cabecera qué mide y por qué.

## Entorno

| | Versión |
|---|---|
| Imagen de cómputo | `tesis-backend:local`, construida con el `Dockerfile` de este repo (Python 3.9, ultralytics 8.3.40, torch 2.8.0+cu128, opencv-python-headless 4.10.0.84) |
| Imagen del agente | `sentinel-agent:local` (Python 3.10, ultralytics 8.3.40, torch 2.8.0+cu128, opencv-python 5.0.0, numpy 2.0.2) |
| YOLOv5 | paquete `yolov5` 7.0.14 instalado sobre `tesis-backend:local` |
| Semilla | 0 en todos los entrenamientos (ultralytics `seed=0, deterministic=True`; yolov5 `--seed 0` por defecto) |
| Hardware de referencia | Laptop, CPU 6 núcleos / 12 hilos, NVIDIA RTX 2070 8 GB (driver con CUDA 12.5), Docker Desktop con VM de 7.6 GB |

Los `.sh` asumen la carpeta de trabajo `BASE` (por defecto
`/d/TESIS BREYNER/dataset_externo_zenodo`); en otra máquina: `BASE=/otra/ruta bash script.sh`.
En Git Bash de Windows hace falta `MSYS_NO_PATHCONV=1` delante de `docker run` (los
scripts ya lo exportan).

## Datos

1. **Dataset propio** (`dataset_80_20`, 21 534 train / 5 386 val) en el volumen Docker
   `tesis-dataset`, montado en `/data`. Ver punto 7 de `ESTADO_CORRECCIONES_FRONTIERS.md`
   sobre su origen y el punto 8 sobre la fuga train/val por aumentos de Roboflow.
2. **Dataset externo** "Dangerous Items" (Zenodo, DOI 10.5281/zenodo.16422779, CC BY 4.0):

   ```bash
   curl -L -o Dangerous_Items.zip "https://zenodo.org/records/16422779/files/Dangerous%20Items.zip?download=1"
   md5sum Dangerous_Items.zip   # f567c3b6e070b2c36578a09c5c7eb9e2
   unzip -q Dangerous_Items.zip -d unpacked
   python remapear.py                 # test  -> eval_dataset/  (5 clases -> 2)
   python remapear_entrenamiento.py   # train+val -> train_dataset/
   ```

   Mapeo de clases verificado mirando imágenes: 0 machete y 1 knife → `arma_blanca`;
   3 rifle y 4 gun → `arma_fuego`; 2 baseball bat → excluida.

## Pasos

| # | Script | Produce |
|---|---|---|
| 1 | `evaluar_externo.py`, `evaluar_completo.py` | Métricas de v3/v4 en el test externo, matriz de confusión, fallos |
| 2 | `entrenar_v4.py` | Modelo v4 (ajuste fino de v3 con train+val de Zenodo) |
| 3 | `test_regresion.py`, `medir_bates.py` | Falsos positivos en lienzos vacíos, mototaxi y bates |
| 4 | `entrenar_yolov5.sh` | YOLOv5s desde COCO, mismo dataset y épocas |
| 5 | `generar_degradaciones.py`, `generar_degradaciones_extra.py`, `evaluar_degradaciones.py` | Test externo con compresión, blur, oclusión, desenfoque y baja luz |
| 6 | `duplicados_phash.py` → `verificar_duplicados.py` → `armar_sin_duplicados.py` | Duplicados entre test externo y entrenamiento; subconjunto limpio de 1 054 imágenes |
| 7 | `cola_noche/cola.sh` | YOLOv8n y YOLOv8s desde COCO, v5 con aumentos de blur/oclusión, y evaluación final de todos los modelos sobre el test sin duplicados |
| 8 | `construir_video.py`, `prueba_carga.sh`, `analizar_carga.sh` | Carga con 1/4/8/16 cámaras simuladas en modo cpu, hilos y gpu |
| 9 | `prueba_red.sh`, `analizar_red.sh` | Latencia de lectura RTSP: UDP/TCP × stream principal/substream (requiere la cámara real y el `.env` del agente) |
| — | `distribucion_fuentes.sh` | Distribución de clases por fuente del dataset propio |

### Montajes de Docker

Los scripts de Python esperan estas rutas dentro del contenedor:

| Ruta | Contenido |
|---|---|
| `/data` | volumen `tesis-dataset` (solo lectura) |
| `/zenodo` | `train_dataset/` |
| `/zenodo_orig` | `unpacked/Dangerous Items/` |
| `/data/eval_dataset`, `/data/degradaciones` | test externo y sus degradaciones (pasos 1, 5) |
| `/ext` | la carpeta `BASE` completa (paso 7) |
| `/modelo/best.pt` | modelo a evaluar o a ajustar |
| `/salida` | salida de entrenamiento o resultados |

Ejemplo, paso 2:

```bash
docker run --rm --gpus all --shm-size=8g \
  -v tesis-dataset:/data:ro \
  -v "$BASE/train_dataset:/zenodo:ro" \
  -v "$BASE/v3_best.pt:/modelo/best.pt:ro" \
  -v "$BASE/data_combinado.yaml:/eval/data_combinado.yaml:ro" \
  -v "$BASE/entrenar_v4.py:/eval/entrenar_v4.py:ro" \
  -v "$BASE/salida_v4:/salida" \
  tesis-backend:local python /eval/entrenar_v4.py
```

`--shm-size=8g` es obligatorio para entrenar: con los 64 MB por defecto los workers de
carga de datos mueren con "bus error".

Paso 7 (un solo contenedor desacoplado; cada etapa se salta si ya terminó, así que se
puede relanzar si se interrumpe):

```bash
docker run -d --name cola_noche --gpus all --shm-size=8g \
  -v tesis-dataset:/data:ro \
  -v "$BASE/train_dataset:/zenodo:ro" \
  -v "$BASE/aug_dataset:/aug" \
  -v "<v4 best.pt>:/modelo/best.pt:ro" \
  -v "<v3 best.pt>:/v3/best.pt:ro" \
  -v "$BASE/cola_noche:/eval:ro" \
  -v "$BASE/salida_noche:/salida" \
  -v "$BASE:/ext" \
  tesis-backend:local sh /eval/cola.sh
```

YOLOv5 (paso 4) intenta descargar `Arial.ttf` de una URL que hoy responde 308 y `urllib`
no sigue: hay que bajarla con `curl -L https://ultralytics.com/assets/Arial.ttf` y montarla
en `/root/.config/Ultralytics/Arial.ttf`.
