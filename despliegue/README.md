# Instalación en los servidores de la municipalidad

Todo Sentinel AI corre en la red de la institución: MongoDB, el backend, el panel de
los operadores (Nginx) y el agente de detección. El video, las imágenes de evidencia y
la base de datos no salen a Internet.

```
Operadores (navegador) ──HTTP──► Nginx :80 ──► panel (React)
                                      │
                                      ├─ /api, /api/v1/ws, /static ──► backend :8000 ──► MongoDB
                                      │
Cámaras RTSP ──► agente ──POST /api/v1/agent/detections──┘
```

## Requisitos del servidor

- Linux de 64 bits con Docker Engine y el plugin `docker compose`.
- 4 núcleos y 8 GB de RAM para MongoDB, el backend, el panel y un agente con pocas
  cámaras en CPU. Con más de unas cuatro cámaras, el agente necesita una GPU NVIDIA
  (driver y NVIDIA Container Toolkit instalados); ver la tabla de carga del artículo.
- Acceso a las cámaras por RTSP desde el equipo donde corra el agente.

## 1. Descargar el código

```bash
sudo mkdir -p /opt/sentinel && cd /opt/sentinel
git clone https://github.com/BREYNERCITO777/BACKEND_PROYECTO_TESIS.git
git clone https://github.com/BREYNERCITO777/FRONTED_PROYECTO_TESIS.git
cd BACKEND_PROYECTO_TESIS/despliegue
```

Si el panel está en otra carpeta, indicar su ruta con `RUTA_PANEL=/ruta/al/panel` en un
archivo `.env` de esta carpeta o en la línea de comandos.

## 2. Configurar

```bash
cp .env.example .env              # claves del backend, retención, dirección del panel
cp agente.env.example agente.env  # solo si el agente corre en este mismo servidor
```

Generar cada clave con `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
`AGENT_TOKEN` debe ser idéntico en `.env` y en `agente.env`.

## 3. Levantar

```bash
docker compose up -d --build                    # MongoDB + backend + panel
docker compose --profile agente up -d --build   # ... más el agente en este servidor
docker compose ps                               # todos en "running"
```

## 4. Crear el primer administrador

```bash
docker compose exec backend python -m app.scripts.crear_admin --email admin@municipalidad.gob.pe --nombre "Administrador"
```

Después, abrir `http://<ip-del-servidor>` en el navegador, entrar con esa cuenta y crear
desde el panel las cuentas de los operadores.

## Agente en otro equipo, junto a las cámaras

Si las cámaras están en otra red o el servidor no tiene GPU, el agente puede correr en
un equipo aparte con `agente/docker-compose.yml`, apuntando al servidor:

```bash
BACKEND_URL=http://<ip-del-servidor>/api/v1/agent/detections
```

## Operación

| Tarea | Comando |
|---|---|
| Ver registros | `docker compose logs -f backend` (o `agente`, `panel`) |
| Actualizar a una versión nueva | `git pull` en los dos repositorios y `docker compose up -d --build` |
| Respaldo de la base de datos | `docker compose exec -T mongo mongodump --archive --gzip > respaldo_$(date +%F).gz` |
| Restaurar un respaldo | `docker compose exec -T mongo mongorestore --archive --gzip --drop < respaldo_AAAA-MM-DD.gz` |

Programar el respaldo diario con `cron` y guardar las copias fuera del servidor.

## Seguridad

- Solo el puerto 80 queda abierto; MongoDB y el backend no publican puertos.
- Para acceder desde fuera de la red interna, poner HTTPS (certificado de la
  institución) delante de Nginx; no exponer el puerto 80 a Internet.
- `.env` y `agente.env` contienen claves y credenciales de las cámaras: permisos
  `chmod 600` y nunca subirlos al repositorio.
- Fijar `EVIDENCE_RETENTION_DAYS` según el plazo que apruebe la institución.
