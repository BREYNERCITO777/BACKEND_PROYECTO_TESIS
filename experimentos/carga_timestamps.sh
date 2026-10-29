#!/bin/bash
# Repite la prueba de carga multicamara (GPU) con timestamps reales de Docker
# en vez del descuento fijo de 15s que tenia analizar_carga.sh. Uso:
# carga_timestamps.sh <N> <duracion_s>
set -e
export MSYS_NO_PATHCONV=1
N=$1
DUR=${2:-70}
BASE="/d/TESIS BREYNER/dataset_externo_zenodo"
CAMARAS="["
for i in $(seq 1 "$N"); do
  [ "$i" -gt 1 ] && CAMARAS="$CAMARAS,"
  CAMARAS="$CAMARAS{\"id\":\"cam_sim_$i\",\"nombre\":\"Simulada $i\",\"rtsp_url\":\"/video/camara_simulada.mp4\"}"
done
CAMARAS="$CAMARAS]"
docker rm -f carga_ts >/dev/null 2>&1 || true
docker run -d --name carga_ts --network tesis-loadtest --gpus all \
  -e CAMARAS="$CAMARAS" \
  -e BACKEND_URL="http://tesis-backend-loadtest:8000/api/v1/agent/detections" \
  -e AGENT_TOKEN="TokenPruebaCarga_2026" \
  -e CONFIDENCE_MIN="0.65" -e ALERT_COOLDOWN="5" \
  -v "$BASE/video_prueba/camara_simulada.mp4:/video/camara_simulada.mp4:ro" \
  sentinel-agent:1.0.0 >/dev/null
echo "N=$N: esperando ${DUR}s..."
sleep "$DUR"
docker stats --no-stream --format "{{.CPUPerc}}\t{{.MemUsage}}" carga_ts > "$BASE/resultados_carga/stats_ts_${N}.txt"
docker logs -t carga_ts > "$BASE/resultados_carga/log_ts_${N}.txt" 2>&1
docker rm -f carga_ts >/dev/null
echo "N=$N listo"
