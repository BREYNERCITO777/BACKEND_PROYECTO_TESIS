#!/bin/bash
# Prueba de carga con N camaras simuladas (Reviewer 1, punto 3).
# Usa el video sintetico en vez de la camara real para no arriesgar
# saturar el unico stream RTSP fisico disponible.
#
# Uso: prueba_carga.sh <N> [duracion_s] [modo]
#   modo cpu   : configuracion original, cada contenedor usa todos los nucleos
#   modo hilos : cada contenedor limitado a NUCLEOS/N hilos (minimo 1), para
#                que no se peleen por la CPU
#   modo gpu   : inferencia en la GPU compartida
set -e
export MSYS_NO_PATHCONV=1

N=$1
DURACION=${2:-90}
MODO=${3:-cpu}
NUCLEOS=$(nproc)
BASE=${BASE:-"/d/TESIS BREYNER/dataset_externo_zenodo"}
RESULTADOS="$BASE/resultados_carga"
mkdir -p "$RESULTADOS"

EXTRA=""
case "$MODO" in
  hilos)
    HILOS=$(( NUCLEOS / N )); [ "$HILOS" -lt 1 ] && HILOS=1
    EXTRA="-e OMP_NUM_THREADS=$HILOS -e MKL_NUM_THREADS=$HILOS"
    ;;
  gpu)
    EXTRA="--gpus all"
    ;;
esac

echo "=== Escenario: $N camara(s), modo $MODO, $DURACION s ==="

for i in $(seq 1 "$N"); do
  docker run -d --name "carga_cam_$i" --network tesis-loadtest $EXTRA \
    -e RTSP_URL="/video/camara_simulada.mp4" \
    -e BACKEND_URL="http://tesis-backend-loadtest:8000/api/v1/agent/detections" \
    -e AGENT_TOKEN="TokenPruebaCarga_2026" \
    -e CAMERA_ID="cam_sim_$i" \
    -e CAMERA_NAME="Simulada $i" \
    -e CONFIDENCE_MIN="0.65" \
    -e ALERT_COOLDOWN="5" \
    -v "$BASE/video_prueba/camara_simulada.mp4:/video/camara_simulada.mp4:ro" \
    sentinel-agent:local > /dev/null
done

sleep 20

> "$RESULTADOS/stats_${MODO}_${N}.txt"
for m in 1 2 3; do
  docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    $(docker ps --filter "name=carga_cam_" --format "{{.Names}}") \
    >> "$RESULTADOS/stats_${MODO}_${N}.txt"
  sleep 15
done

RESTANTE=$((DURACION - 20 - 45))
[ "$RESTANTE" -gt 0 ] && sleep "$RESTANTE"

> "$RESULTADOS/latencia_${MODO}_${N}.txt"
for i in $(seq 1 "$N"); do
  docker logs "carga_cam_$i" >> "$RESULTADOS/latencia_${MODO}_${N}.txt" 2>&1
  docker rm -f "carga_cam_$i" > /dev/null
done

echo "=== Escenario $N ($MODO) completo ==="
