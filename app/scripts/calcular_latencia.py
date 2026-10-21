"""Calcula mediana y P95 de latencia a partir de los logs del backend.

Lee lineas del logger "sentinel.latency" (ver app/routers/agent.py) y arma la
tabla que pide el plan de correcciones de Frontiers: FPS/latencia por
escenario. No inventa numeros — si no hay lineas que parsear, lo dice y no
imprime nada.

Uso:
    uvicorn app.main:app ... > backend.log 2>&1
    python app/scripts/calcular_latencia.py backend.log
"""
import re
import statistics
import sys

PATRON = re.compile(
    r"camera_id=(?P<cam>\S+) inferencia_ms=(?P<inf>[\d.]+|NA) "
    r"preproc_ms=(?P<pre>[\d.]+|NA) backend_ms=(?P<back>[\d.]+) "
    r"agente_a_backend_ms=(?P<red>[\d.]+|NA)"
)


def percentil(valores, p):
    if not valores:
        return None
    s = sorted(valores)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def main(ruta_log):
    inferencia, preproc, backend, red = [], [], [], []

    with open(ruta_log, encoding="utf-8", errors="ignore") as f:
        for linea in f:
            m = PATRON.search(linea)
            if not m:
                continue
            if m["inf"] != "NA":
                inferencia.append(float(m["inf"]))
            if m["pre"] != "NA":
                preproc.append(float(m["pre"]))
            backend.append(float(m["back"]))
            if m["red"] != "NA":
                red.append(float(m["red"]))

    if not backend:
        print(f"No se encontraron líneas de latencia en {ruta_log}. "
              "¿El logger 'sentinel.latency' está en nivel INFO?")
        return

    def reportar(nombre, valores):
        if not valores:
            print(f"  {nombre:20s}: sin datos")
            return
        print(
            f"  {nombre:20s}: n={len(valores):4d}  "
            f"P50={percentil(valores, 0.50):7.1f} ms  "
            f"P95={percentil(valores, 0.95):7.1f} ms  "
            f"max={max(valores):7.1f} ms"
        )

    print("=" * 60)
    print("LATENCIA — resumen (ver Protocolo específico de latencia operativa)")
    print("=" * 60)
    reportar("Inferencia (agente)", inferencia)
    reportar("Preproc+JPEG (agente)", preproc)
    reportar("Persistencia (backend)", backend)
    reportar("Agente→backend (red)", red)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python calcular_latencia.py <archivo_de_log>")
        sys.exit(1)
    main(sys.argv[1])
