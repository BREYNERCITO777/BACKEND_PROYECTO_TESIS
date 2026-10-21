#!/bin/bash
# Resume resultados de prueba_carga.sh por modo y numero de camaras.
# Descarta el primer frame de cada camara (carga del modelo en memoria).
# Uso: analizar_carga.sh [duracion_s]
R="${BASE:-/d/TESIS BREYNER/dataset_externo_zenodo}/resultados_carga"
DURACION=${1:-90}

pct() {
  local n; n=$(wc -l < "$1")
  [ "$n" -eq 0 ] && { echo "NA"; return; }
  sed -n "$(( (n - 1) * $2 / 100 + 1 ))p" "$1"
}

printf "%-6s %4s %7s %8s %9s %9s %9s %9s %9s %8s\n" \
  modo N frames fps/cam inf_P50 inf_P95 lect_P50 lect_P95 cpu_tot ram_MiB
for modo in cpu hilos gpu; do
  for N in 1 4 8 16; do
    log="$R/latencia_${modo}_${N}.txt"
    [ -f "$log" ] || continue
    awk '/LATENCIA_FRAME/ {
           match($0, /cam=[^ ]+/); cam = substr($0, RSTART, RLENGTH)
           if (visto[cam]++ == 0) next
           match($0, /inferencia_ms=[0-9.]+/); print substr($0, RSTART+14, RLENGTH-14) > "/tmp/inf"
           match($0, /lectura_ms=[0-9.]+/);    print substr($0, RSTART+11, RLENGTH-11) > "/tmp/lect"
         }' "$log"
    sort -n /tmp/inf -o /tmp/inf; sort -n /tmp/lect -o /tmp/lect
    frames=$(wc -l < /tmp/inf)
    fps=$(awk -v f="$frames" -v n="$N" -v d="$DURACION" 'BEGIN{printf "%.2f", f/(d-15)/n}')
    cpu=$(awk -F'\t' '{gsub("%","",$2); s+=$2} END{printf "%.0f%%", s/3}' "$R/stats_${modo}_${N}.txt")
    ram=$(awk -F'\t' '{split($3,a," "); v=a[1]; if (v ~ /GiB/) {gsub("GiB","",v); v*=1024} else gsub("MiB","",v); s+=v; n++} END{printf "%.0f", s/n}' "$R/stats_${modo}_${N}.txt")
    printf "%-6s %4s %7s %8s %9s %9s %9s %9s %9s %8s\n" "$modo" "$N" "$frames" "$fps" \
      "$(pct /tmp/inf 50)" "$(pct /tmp/inf 95)" "$(pct /tmp/lect 50)" "$(pct /tmp/lect 95)" "$cpu" "$ram"
    rm -f /tmp/inf /tmp/lect
  done
done
