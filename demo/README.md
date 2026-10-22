# Demo de punta a punta

Levanta MongoDB, el backend y el agente YOLO leyendo `video_demo.mp4` como si fuera
una cámara. Desde la raíz del repositorio:

```bash
docker compose -f demo/docker-compose.yml up --build
```

La primera vez tarda varios minutos (instala torch). En menos de un minuto de
funcionamiento deberían aparecer alertas:

```bash
docker compose -f demo/docker-compose.yml logs agente | grep "ALERTA ENVIADA"
docker compose -f demo/docker-compose.yml exec mongo mongosh sentinel_demo --eval "db.incidents.countDocuments()"
```

La documentación de la API queda en <http://localhost:8000/docs>. Para terminar y
borrar los datos de la demo:

```bash
docker compose -f demo/docker-compose.yml down -v
```

Para usar una cámara real o tu propio video, cambia `RTSP_URL` del servicio `agente`
(una URL `rtsp://...` o la ruta de un archivo montado).

## El video

`video_demo.mp4`: 60 imágenes (40 con armas, 20 sin) del split de prueba, sin
duplicados, del dataset **Dangerous Items**, a 2 imágenes por segundo (30 s). Los
nombres de archivo están en `video_demo_fuentes.txt`. Licencia CC BY 4.0; cita
requerida:

Omiotek, Z. (2025). Effectiveness of Modern Models Belonging to the YOLO and Vision
Transformer Architectures in Dangerous Items Detection. *Electronics*, 14(17), 3540.
https://doi.org/10.3390/electronics14173540 — Dataset: Zenodo,
https://doi.org/10.5281/zenodo.16422779
