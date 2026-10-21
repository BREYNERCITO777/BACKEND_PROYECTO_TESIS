#!/bin/sh
# Cola nocturna: corre dentro de un solo contenedor desacoplado para
# sobrevivir aunque se cierre la sesion. Cada paso deja una marca en
# /salida/progreso.log para poder seguirla desde afuera.
#
# Si un entrenamiento muere despues de guardar sus pesos (paso 1, primera
# corrida: la validacion final de ultralytics agoto la RAM de la VM de
# Docker), se registra y se sigue con el siguiente paso en vez de abortar.
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a /salida/progreso.log; }

# best.pt se guarda en cada epoca: que exista no prueba que el entrenamiento
# haya terminado. Se considera completo solo si results.csv tiene 20 epocas.
completo() {  # completo <best.pt>
  csv="$(dirname "$(dirname "$1")")/results.csv"
  epocas=$(( $(wc -l < "$csv" 2>/dev/null || echo 1) - 1 ))
  [ -f "$1" ] && [ "$epocas" -eq 20 ]
}

entrenar() {  # entrenar <nombre_log> <best.pt esperado> <comando...>
  nombre=$1; pesos=$2; shift 2
  if completo "$pesos"; then
    log "$nombre: ya completo, se salta"
    return 0
  fi
  log "$nombre: inicio"
  if "$@"; then
    log "$nombre: fin"
    return 0
  fi
  if completo "$pesos"; then
    log "$nombre: el proceso fallo despues de completar 20 epocas, se continua"
  else
    log "$nombre: FALLO ($epocas epocas), se aborta la cola"
    exit 1
  fi
}

log "INICIO cola"

entrenar "yolov8n desde COCO" /salida/yolov8n_coco/weights/best.pt \
  python /eval/entrenar_coco.py yolov8n.pt yolov8n_coco

entrenar "yolov8s desde COCO" /salida/yolov8s_coco/weights/best.pt \
  python /eval/entrenar_coco.py yolov8s.pt yolov8s_coco

if [ ! -d /aug/images/train ] || [ -z "$(ls -A /aug/images/train)" ]; then
  log "aumentos blur/oclusion: inicio"
  python /eval/generar_aumentos.py || { log "aumentos: FALLO"; exit 1; }
  log "aumentos blur/oclusion: fin"
fi

entrenar "v5 (v4 + aumentos)" /salida/modelo_v5/weights/best.pt \
  python /eval/entrenar_v5.py

log "evaluacion final: inicio"
python /eval/evaluar_todo.py || { log "evaluacion final: FALLO"; exit 1; }
log "FIN cola"
