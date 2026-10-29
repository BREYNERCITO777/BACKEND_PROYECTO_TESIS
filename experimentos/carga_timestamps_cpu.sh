#!/bin/bash
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
docker rm -f carga_ts_cpu >/dev/null 2>&1 || true
docker run -d --name carga_ts_cpu --network tesis-loadtest \
  -e CAMARAS="$CAMARAS" \
  -e BACKEND_URL="http://tesis-backend-loadtest:8000/api/v1/agent/detections" \
  -e AGENT_TOKEN="TokenPruebaCarga_2026" \
  -e CONFIDENCE_MIN="0.65" -e ALERT_COOLDOWN="5" \
  -e CUDA_VISIBLE_DEVICES="" \
  -v "$BASE/video_prueba/camara_simulada.mp4:/video/camara_simulada.mp4:ro" \
  sentinel-agent:1.0.0 >/dev/null
echo "CPU N=$N: esperando ${DUR}s..."
sleep "$DUR"
docker logs -t carga_ts_cpu > "$BASE/resultados_carga/log_ts_cpu_${N}.txt" 2>&1
docker rm -f carga_ts_cpu >/dev/null
echo "CPU N=$N listo"
