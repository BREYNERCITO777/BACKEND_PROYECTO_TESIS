"""Latencia captura -> recepcion en el cliente WebSocket, por alerta:
  inferencia_ms + preproc_ms (log del agente) + (llegada al cliente - marca de
  tiempo del payload, tomada justo antes del POST).
Cada mensaje WebSocket se empareja con su linea LATENCIA del agente por camara
y por tiempo (hora del log - red_ms ~ marca del payload). Se descartan las
alertas del primer lote (calentamiento CUDA), igual que en la Tabla 5."""
import json
import re
from datetime import datetime

import numpy as np


def ts(s):
    s = s.replace("Z", "+00:00")
    base, _, resto = s.partition(".")
    frac, signo, zona = re.match(r"(\d+)([+-])(.*)", resto).groups()
    return datetime.fromisoformat(f"{base}.{frac[:6]}{signo}{zona}").timestamp()


resumen = {}
for n in (1, 4, 8, 16):
    agente = []
    for linea in open(f"agente_{n}.txt", encoding="utf-8", errors="ignore"):
        m = re.match(r"(\S+) LATENCIA cam=(\S+) inferencia_ms=([\d.]+) preproc_ms=([\d.]+) red_ms=([\d.]+)", linea)
        if m:
            t, cam, inf, pre, red = m.groups()
            agente.append({"cam": cam, "envio": ts(t) - float(red) / 1000, "inf": float(inf), "pre": float(pre)})
    # primer lote de inferencia del agente (CUDA): su tiempo, de LATENCIA_FRAME
    texto = open(f"agente_{n}.txt", encoding="utf-8", errors="ignore").read()
    primer_lote = float(re.search(r"LATENCIA_FRAME .*?inferencia_ms=([\d.]+)", texto).group(1))
    calentamiento = sum(1 for a in agente if a["inf"] == primer_lote)
    agente = [a for a in agente if a["inf"] != primer_lote]
    ws = [json.loads(l) for l in open(f"ws_{n}.jsonl")]
    totales, cliente = [], []
    usados = set()
    for w in ws:
        t_payload = ts(w["timestamp"])
        cands = [(abs(a["envio"] - t_payload), i) for i, a in enumerate(agente)
                 if a["cam"] == w["camera_id"] and i not in usados]
        if not cands:
            continue
        dif, i = min(cands)
        if dif > 0.5:
            continue
        usados.add(i)
        c = (w["recv"] - t_payload) * 1000
        cliente.append(c)
        totales.append(agente[i]["inf"] + agente[i]["pre"] + c)
    p = lambda v, q: float(np.percentile(v, q, method="nearest"))
    resumen[n] = {"alertas": len(totales), "calentamiento_descartadas": calentamiento,
                  "captura_a_cliente_P50": round(p(totales, 50), 1), "captura_a_cliente_P95": round(p(totales, 95), 1),
                  "envio_a_cliente_P50": round(p(cliente, 50), 1), "envio_a_cliente_P95": round(p(cliente, 95), 1)}
    print(n, resumen[n])
json.dump(resumen, open("resumen_e2e_cliente.json", "w"), indent=2)
