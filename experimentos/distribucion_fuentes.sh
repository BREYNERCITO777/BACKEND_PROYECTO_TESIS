#!/bin/sh
# Distribucion de objetos por clase segun el prefijo del nombre de archivo
# (pista del dataset de origen), en todo dataset_80_20. Corre dentro de alpine.
cd /data/dataset_80_20
for s in train val; do
  for f in $s/labels/*.txt; do
    b=$(basename "$f" .txt)
    p=$(echo "$b" | sed -E 's/^(aug_)?//; s/[-_ (].*//; s/[0-9]{6,}.*/FECHA/; s/[0-9]+$//')
    if [ -s "$f" ]; then
      awk -v p="$p" '{print p, $1}' "$f"
    else
      echo "$p fondo"
    fi
  done
done | awk '{
  n[$1]++
  if ($2 == "0") f[$1]++
  else if ($2 == "1") b[$1]++
  else g[$1]++
} END {
  printf "%-14s %8s %10s %11s %7s\n", "prefijo", "objetos", "arma_fuego", "arma_blanca", "fondo"
  for (k in n) printf "%-14s %8d %10d %11d %7d\n", k, n[k], f[k], b[k], g[k]
}' | sort -k2 -nr
