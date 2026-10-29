#!/bin/bash
# Latencia captura -> recepcion en un cliente WebSocket (el que usaria el
# panel), con 1/4/8/16 camaras simuladas en GPU. MongoDB y backend desechables
# en la red tesis-loadtest; nada toca produccion. Uso: e2e_cliente.sh [duracion_s]
set -e
export MSYS_NO_PATHCONV=1
DUR=${1:-90}
BASE="/d/TESIS BREYNER/dataset_externo_zenodo"
OUT="$BASE/e2e_cliente"
docker rm -f e2e_mongo e2e_backend e2e_ws e2e_agente >/dev/null 2>&1 || true
docker run -d --name e2e_mongo --network tesis-loadtest mongo:7 >/dev/null
docker run -d --name e2e_backend --network tesis-loadtest \
  -e MONGO_URL="mongodb://e2e_mongo:27017" -e MONGO_DB="e2e_prueba" \
  -e AGENT_TOKEN="TokenPruebaCarga_2026" -e JWT_SECRET="solo-prueba-e2e" \
  sentinel-backend:1.0.0 uvicorn app.main:app --host 0.0.0.0 --port 8000 >/dev/null
sleep 15
for N in 1 4 8 16; do
  rm -f "$OUT/ws_$N.jsonl"
  docker rm -f e2e_ws >/dev/null 2>&1 || true
  docker run -d --name e2e_ws --network tesis-loadtest -v "$OUT:/out" \
    sentinel-backend:1.0.0 python /out/cliente_ws.py ws://e2e_backend:8000/api/v1/ws/alerts "/out/ws_$N.jsonl" >/dev/null
  sleep 5
  CAMARAS="["
  for i in $(seq 1 "$N"); do
    [ "$i" -gt 1 ] && CAMARAS="$CAMARAS,"
    CAMARAS="$CAMARAS{\"id\":\"cam_sim_$i\",\"nombre\":\"Simulada $i\",\"rtsp_url\":\"/video/camara_simulada.mp4\"}"
  done
  CAMARAS="$CAMARAS]"
  docker run -d --name e2e_agente --network tesis-loadtest --gpus all \
    -e CAMARAS="$CAMARAS" \
    -e BACKEND_URL="http://e2e_backend:8000/api/v1/agent/detections" \
    -e AGENT_TOKEN="TokenPruebaCarga_2026" \
    -e CONFIDENCE_MIN="0.65" -e ALERT_COOLDOWN="5" \
    -v "$BASE/video_prueba/camara_simulada.mp4:/video/camara_simulada.mp4:ro" \
    sentinel-agent:1.0.0 >/dev/null
  echo "N=$N corriendo ${DUR}s..."
  sleep "$DUR"
  docker logs -t e2e_agente > "$OUT/agente_$N.txt" 2>&1
  docker rm -f e2e_agente e2e_ws >/dev/null
  sleep 5
done
docker logs e2e_backend > "$OUT/backend.txt" 2>&1
docker rm -f e2e_mongo e2e_backend >/dev/null
echo listo
