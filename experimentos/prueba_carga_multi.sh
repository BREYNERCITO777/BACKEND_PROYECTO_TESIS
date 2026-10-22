#!/bin/bash
# Prueba de carga del agente multicamara: UN contenedor con N camaras
# simuladas y un solo modelo compartido (comparar con prueba_carga.sh, que
# levanta un contenedor por camara).
# Uso: prueba_carga_multi.sh <N> [duracion_s] [cpu|gpu] [imagen]
set -e
export MSYS_NO_PATHCONV=1

N=$1
DURACION=${2:-90}
MODO=${3:-gpu}
IMAGEN=${4:-sentinel-agent:local}
BASE=${BASE:-"/d/TESIS BREYNER/dataset_externo_zenodo"}
RESULTADOS="$BASE/resultados_carga"
mkdir -p "$RESULTADOS"

CAMARAS="["
for i in $(seq 1 "$N"); do
  [ "$i" -gt 1 ] && CAMARAS="$CAMARAS,"
  CAMARAS="$CAMARAS{\"id\":\"cam_sim_$i\",\"nombre\":\"Simulada $i\",\"rtsp_url\":\"/video/camara_simulada.mp4\"}"
done
CAMARAS="$CAMARAS]"

EXTRA=""
[ "$MODO" = "gpu" ] && EXTRA="--gpus all"

echo "=== Multicamara: $N camaras en un proceso, modo $MODO, $DURACION s ==="
docker run -d --name carga_multi --network tesis-loadtest $EXTRA \
  -e CAMARAS="$CAMARAS" \
  -e BACKEND_URL="http://tesis-backend-loadtest:8000/api/v1/agent/detections" \
  -e AGENT_TOKEN="TokenPruebaCarga_2026" \
  -e CONFIDENCE_MIN="0.65" -e ALERT_COOLDOWN="5" \
  -v "$BASE/video_prueba/camara_simulada.mp4:/video/camara_simulada.mp4:ro" \
  "$IMAGEN" > /dev/null

sleep 20
> "$RESULTADOS/stats_multi${MODO}_${N}.txt"
for m in 1 2 3; do
  docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" carga_multi \
    >> "$RESULTADOS/stats_multi${MODO}_${N}.txt"
  sleep 15
done
RESTANTE=$((DURACION - 20 - 45))
[ "$RESTANTE" -gt 0 ] && sleep "$RESTANTE"

docker logs carga_multi > "$RESULTADOS/latencia_multi${MODO}_${N}.txt" 2>&1
docker rm -f carga_multi > /dev/null
echo "=== Multicamara $N ($MODO) completo ==="
