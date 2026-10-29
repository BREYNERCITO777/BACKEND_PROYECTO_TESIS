"""Recalcula, desde los logs crudos de esta carpeta, las cifras de la Tabla 5
(FPS por camara, P50/P95 de inferencia) y la latencia extremo a extremo por
carga. Regla unica: se descarta el primer lote de cada corrida (inicializacion
de CUDA y del modelo, 2.3-3.5 s); percentil por rango mas cercano.
Uso: python recalcular.py"""
import os
import re
from datetime import datetime

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))


def leer(*p):
    return open(os.path.join(AQUI, *p), encoding="utf-8", errors="ignore").read()


def ts(s):
    return datetime.fromisoformat(s[:26])


print("Tabla 5  (frames contados despues de la inferencia: LATENCIA_FRAME)")
for dev, pref in (("GPU", "log_ts_"), ("CPU", "log_ts_cpu_")):
    for n in (1, 4, 8, 16):
        s = leer("logs_fps_timestamps", f"{pref}{n}.txt")
        marcas = re.findall(r"^(\S+)Z LATENCIA_FRAME", s, re.M)
        inf = [float(x) for x in re.findall(r"LATENCIA_FRAME .*?inferencia_ms=([\d.]+)", s)][n:]
        dur = (ts(marcas[-1]) - ts(marcas[0])).total_seconds()
        print(f"  {dev} N={n:2d}  frames={len(marcas):5d}  duracion={dur:6.1f}s  "
              f"FPS/camara={len(marcas) / dur / n:.2f}  inferencia P50={np.percentile(inf, 50, method="nearest"):.1f} "
              f"P95={np.percentile(inf, 95, method="nearest"):.1f} ms")

print("\nLatencia captura -> alerta en MongoDB + WebSocket (total_agente_ms por alerta)")
casos = [("GPU", 1, "latencia_multigpu_1.txt", 1), ("GPU", 4, "e2e_log_4.txt", 4),
         ("GPU", 8, "e2e_log_8.txt", 0), ("GPU", 16, "latencia_multigpu_16.txt", 0),
         ("CPU", 1, "latencia_multicpu_1.txt", 0)]
for dev, n, f, calentamiento in casos:
    v = [float(x) for x in re.findall(r"LATENCIA cam=\S+ .*?total_agente_ms=([\d.]+)",
                                      leer("logs_latencia_e2e", f))][calentamiento:]
    print(f"  {dev} N={n:2d}  alertas={len(v):3d} (descartadas por calentamiento CUDA: {calentamiento})  "
          f"P50={np.percentile(v, 50, method="nearest"):.1f}  P95={np.percentile(v, 95, method="nearest"):.1f}  "
          f"min={min(v):.0f}  max={max(v):.0f} ms")
