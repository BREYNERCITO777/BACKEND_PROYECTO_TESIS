#!/bin/bash
# Resume los logs de prueba_red.sh: P50/P95 de lectura e inferencia, frames,
# errores RTP (bad cseq) y CPU.
OUT="${BASE:-/d/TESIS BREYNER/dataset_externo_zenodo}/resultados_red"
DURACION=${1:-120}

pct() {  # pct <archivo_ordenado> <p>
  local n; n=$(wc -l < "$1")
  [ "$n" -eq 0 ] && { echo "NA"; return; }
  sed -n "$(( (n - 1) * $2 / 100 + 1 ))p" "$1"
}

printf "%-14s %7s %6s %10s %10s %10s %10s %6s %6s\n" \
  config frames fps lect_P50 lect_P95 inf_P50 inf_P95 cseq cpu
for c in udp_principal tcp_principal udp_sub tcp_sub; do
  log="$OUT/log_$c.txt"
  [ -f "$log" ] || continue
  # se descarta el primer frame (carga del modelo en memoria)
  grep -o "lectura_ms=[0-9.]*" "$log" | tail -n +2 | cut -d= -f2 | sort -n > /tmp/lect_$c
  grep -o "inferencia_ms=[0-9.]*" "$log" | tail -n +2 | cut -d= -f2 | sort -n > /tmp/inf_$c
  frames=$(wc -l < /tmp/inf_$c)
  fps=$(awk -v f="$frames" -v d="$DURACION" 'BEGIN{printf "%.2f", f/(d-15)}')
  cseq=$(grep -c "bad cseq" "$log")
  cpu=$(cat "$OUT/cpu_$c.txt" 2>/dev/null)
  printf "%-14s %7s %6s %10s %10s %10s %10s %6s %6s\n" \
    "$c" "$frames" "$fps" "$(pct /tmp/lect_$c 50)" "$(pct /tmp/lect_$c 95)" \
    "$(pct /tmp/inf_$c 50)" "$(pct /tmp/inf_$c 95)" "$cseq" "$cpu"
done
