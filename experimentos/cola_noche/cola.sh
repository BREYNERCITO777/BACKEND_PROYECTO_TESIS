#!/bin/sh
# Cola nocturna: corre dentro de un solo contenedor desacoplado para
# sobrevivir aunque se cierre la sesion. Cada paso deja una marca en
# /salida/progreso.log para poder seguirla desde afuera.
set -e
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a /salida/progreso.log; }

log "INICIO cola"

if [ ! -f /salida/yolov8n_coco/weights/best.pt ]; then
  log "yolov8n desde COCO: inicio"
  python /eval/entrenar_coco.py yolov8n.pt yolov8n_coco
  log "yolov8n desde COCO: fin"
fi

if [ ! -f /salida/yolov8s_coco/weights/best.pt ]; then
  log "yolov8s desde COCO: inicio"
  python /eval/entrenar_coco.py yolov8s.pt yolov8s_coco
  log "yolov8s desde COCO: fin"
fi

if [ ! -d /aug/images/train ] || [ -z "$(ls -A /aug/images/train)" ]; then
  log "aumentos blur/oclusion: inicio"
  python /eval/generar_aumentos.py
  log "aumentos blur/oclusion: fin"
fi

if [ ! -f /salida/modelo_v5/weights/best.pt ]; then
  log "v5 (v4 + aumentos): inicio"
  python /eval/entrenar_v5.py
  log "v5: fin"
fi

log "evaluacion final: inicio"
python /eval/evaluar_todo.py
log "FIN cola"
