"""Cliente WebSocket que hace de panel: se suscribe a /ws/alerts y anota, por
cada alerta, la hora de llegada (reloj de pared del host, el mismo que usa el
agente: todos los contenedores corren en la misma VM de Docker)."""
import asyncio
import json
import sys
import time

import websockets

URL = sys.argv[1]
SALIDA = sys.argv[2]


async def main():
    while True:
        try:
            async with websockets.connect(URL, max_size=None) as ws:
                print("conectado", flush=True)
                with open(SALIDA, "a") as f:
                    while True:
                        msg = await ws.recv()
                        t = time.time()
                        d = json.loads(msg)
                        a = d.get("data") or {}
                        f.write(json.dumps({"recv": t, "event": d.get("event"),
                                            "camera_id": a.get("camera_id"),
                                            "timestamp": a.get("timestamp")}) + "\n")
                        f.flush()
        except Exception as e:  # el backend aun no arranca
            print("reintento:", repr(e), flush=True)
            await asyncio.sleep(1)


asyncio.run(main())
