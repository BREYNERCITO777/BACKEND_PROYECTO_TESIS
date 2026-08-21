# Sentinel AI — Backend

API del sistema de detección de armas de la **Municipalidad Provincial de San
Martín**. Recibe las detecciones que produce el modelo YOLO, decide cuáles son
incidentes reales, guarda la evidencia y avisa al operador en tiempo real.

---

## Cómo funciona

El modelo **no** corre en este servidor. Corre en un equipo dentro de la
municipalidad, junto a las cámaras, porque el video no sale de la red local.
Ese agente envía únicamente el resultado de cada detección:

```
  Cámara IP  ──RTSP──▶  Agente YOLO        ──HTTPS──▶  Backend  ──▶  MongoDB
  (red local)           (equipo local)      + token        │
                                                           └──WebSocket──▶ Panel
                                                                           del operador
```

**El agente nunca toca la base de datos.** Escribe solo el backend. Esto no es
un detalle de estilo: es lo que permite aplicar el umbral de confianza, el
control anti-avalancha y la validación de datos en un único sitio. Si el agente
escribiera directo, cada una de esas reglas habría que repetirla y mantenerla
en dos lugares.

Cuando llega una detección, el backend decide en este orden:

1. **¿El token es válido?** Si no → `401` y no pasa nada más.
2. **¿Los datos tienen sentido?** Confianza entre 0 y 1, fecha en ISO 8601,
   imagen en base64 correcta y por debajo del límite. Si no → `422`.
3. **¿Supera el umbral de confianza?** El umbral vive en la configuración del
   panel, no en el código. Si no lo supera → se responde `200` con
   `ignorada: true`, motivo `confianza_bajo_umbral`.
4. **¿Esa cámara acaba de avisar?** Un agente detectando a 10 fps generaría 10
   incidentes por segundo. Hay un tiempo de espera **por cámara** (5 s por
   defecto): silenciar una no silencia a las demás.
5. Si pasa todo: se crea el incidente, se crea la alerta enlazada a él y se
   empuja al panel por WebSocket.

Que una detección descartada responda `200` y no un error es deliberado:
descartarla es el funcionamiento normal, no un fallo del agente.

---

## Puesta en marcha

Necesitas Python 3.9+ y MongoDB.

```bash
pip install -r requirements.txt

cp .env.example .env      # y rellena AGENT_TOKEN y JWT_SECRET

uvicorn app.main:app --reload
```

La documentación interactiva queda en <http://localhost:8000/docs>.

Con Docker:

```bash
docker build -t sentinel-backend .
docker run -p 8000:8000 --env-file .env sentinel-backend
```

### Si no arranca

**`AGENT_TOKEN no está configurado`** — es intencionado. El backend se niega a
arrancar sin él en lugar de usar un token de respaldo escrito en el código, que
dejaría la puerta abierta a cualquiera que leyera el repositorio. Defínelo en
el `.env`.

**El navegador bloquea las peticiones** — la dirección del frontend no está en
`CORS_ORIGINS`. Van separadas por comas y sin barra final.

**El agente recibe `401`** — su `AGENT_TOKEN` y el del backend no coinciden.
Deben ser idénticos, carácter por carácter.

---

## Configuración

Todas las variables están documentadas en [`.env.example`](.env.example). Las
dos imprescindibles:

| Variable | Para qué sirve |
|---|---|
| `AGENT_TOKEN` | Credencial compartida con el agente YOLO. Sin ella el backend no arranca. |
| `JWT_SECRET` | Firma las sesiones. Quien la conozca puede fabricarse un token de administrador. |

Genera ambas con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

El **umbral de confianza no es una variable de entorno**: se ajusta desde el
panel (Configuración) y gobierna todo el sistema, incluida la inferencia
interna. `CONF_TH` solo actúa la primera vez, cuando aún no existe la
configuración en la base.

---

## Endpoints

Todos cuelgan de `/api/v1`.

| | |
|---|---|
| `POST /auth/login` | Devuelve el token de sesión. Formulario, no JSON. |
| `GET /users/me` | La cuenta actual. |
| `GET·POST·PATCH·DELETE /users` | Gestión de cuentas. Solo administrador. |
| `POST /agent/detections` | **Camino crítico.** Lo que envía el agente YOLO. |
| `POST /inference/detectar` | Detección sobre una foto subida a mano. |
| `GET /inference/stream/{camera_id}` | Video en vivo con las detecciones dibujadas. |
| `GET·POST·PATCH·DELETE /cameras` | Gestión de cámaras. |
| `GET·DELETE /incidents` | Historial de incidentes y su evidencia. |
| `GET /alerts`, `PATCH /alerts/{id}/read` | Bandeja del operador. |
| `GET·PATCH /settings` | Umbral de confianza y demás ajustes. |
| `WS /ws/alerts` | Alertas empujadas al panel en tiempo real. |

Hay dos roles: **admin** (todo) y **operator** (consulta incidentes y alertas,
no administra cuentas ni cámaras).

---

## Decisiones que conviene conocer antes de tocar el código

**Las credenciales RTSP se guardan cifradas.** Las URL de las cámaras llevan
usuario y contraseña. Se cifran con Fernet antes de entrar a Mongo y la API las
devuelve enmascaradas; solo se descifran en el momento de abrir el video.
Como el cifrado no es determinista, el índice único que impide duplicar una
cámara va sobre una huella SHA-256, no sobre el texto cifrado.

**La evidencia se guarda dos veces.** Como archivo, para servir las imágenes
por HTTP sin inflar la API, y como copia en base64 dentro del incidente. La
copia existe porque el sistema de archivos del contenedor se descarta en cada
despliegue: los incidentes quedaban apuntando a imágenes que ya no existían.

**Las evidencias no se versionan.** Son fotogramas reales de la vía pública con
personas identificables. El directorio `app/static/` está en `.gitignore` y la
aplicación lo crea sola al arrancar.

**El interruptor de notificaciones por correo no envía correos.** Está marcado
como no implementado en la documentación de la API. Se guarda el ajuste, pero
no existe ninguna línea que mande un email.

**Todo el acceso a datos pasa por `app/repositories/`.** Los routers no hablan
con Mongo directamente.

---

## Pruebas

```bash
pytest tests/ -v
```

Se ejecutan contra la API y MongoDB reales, no contra objetos simulados, porque
los fallos que ha tenido este proyecto han sido de integración. El detalle está
en [`tests/README.md`](tests/README.md).

`tests/test_regresiones.py` merece una mención aparte: cada prueba corresponde
a un fallo que ya ocurrió una vez, con el motivo explicado. Si una falla, lee
su documentación antes de tocar nada.

---

## Estructura

```
app/
  core/          configuración, base de datos, seguridad, cifrado, arranque
  models/        esquemas Pydantic y los pesos del modelo YOLO
  repositories/  acceso a datos — el único sitio que habla con Mongo
  routers/       endpoints HTTP y WebSocket
  services/      detección, evidencia, gestión de cámaras
tests/           pruebas contra el sistema real
```
