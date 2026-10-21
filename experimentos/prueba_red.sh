#!/bin/bash
# Compara transporte RTSP (UDP vs TCP) y stream (principal 1080p vs substream)
# contra la camara real, para el punto 6 de limitaciones (jitter de red).
# Uso: prueba_red.sh <segundos_por_config>
set -e
export MSYS_NO_PATHCONV=1

DURACION=${1:-120}
BASE=${BASE:-"/d/TESIS BREYNER/dataset_externo_zenodo"}
OUT="$BASE/resultados_red"
mkdir -p "$OUT"

# Credenciales leidas del .env del agente, no escritas en este script.
ENV_AGENTE=${ENV_AGENTE:-"/d/TESIS BREYNER/BACKEND_PROYECTO_TESIS-main/sentinel-agent/.env"}
BASE_URL=$(grep '^RTSP_URL=' "$ENV_AGENTE" | cut -d= -f2- | sed 's/subtype=[0-9]*/subtype=SUB/')

correr() {
  local nombre=$1 subtype=$2 transporte=$3
  local url=${BASE_URL/subtype=SUB/subtype=$subtype}
  local opciones=""
  [ "$transporte" = "tcp" ] && opciones="rtsp_transport;tcp"

  echo "=== $nombre (subtype=$subtype, $transporte), ${DURACION}s ==="
  docker run -d --name "red_$nombre" --network tesis-loadtest \
    -e RTSP_URL="$url" \
    -e OPENCV_FFMPEG_CAPTURE_OPTIONS="$opciones" \
    -e BACKEND_URL="http://tesis-backend-loadtest:8000/api/v1/agent/detections" \
    -e AGENT_TOKEN="TokenPruebaCarga_2026" \
    -e CAMERA_ID="red_$nombre" -e CAMERA_NAME="Prueba red $nombre" \
    -e CONFIDENCE_MIN="0.65" -e ALERT_COOLDOWN="5" \
    sentinel-agent:local > /dev/null

  sleep 20
  docker stats --no-stream --format "{{.CPUPerc}}" "red_$nombre" > "$OUT/cpu_$nombre.txt"
  sleep $((DURACION - 20))
  docker logs "red_$nombre" > "$OUT/log_$nombre.txt" 2>&1
  docker rm -f "red_$nombre" > /dev/null
}

correr udp_principal 0 udp
correr tcp_principal 0 tcp
correr udp_sub 1 udp
correr tcp_sub 1 tcp
echo "=== Listo ==="
