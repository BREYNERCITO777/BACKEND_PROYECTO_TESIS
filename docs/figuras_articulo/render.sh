#!/bin/sh
# Renderiza figN.html a figN.png (escala 2) con Edge headless.
# Uso: sh render.sh fig2 1500 1010
cd "$(dirname "$0")"
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --virtual-time-budget=3000 --window-size="$2,$3" \
  --screenshot="$(cygpath -w "$PWD/$1.png")" "file:///$(cygpath -m "$PWD/$1.html")" >/dev/null 2>&1
ls -la "$1.png" | awk '{print $5, $NF}'
