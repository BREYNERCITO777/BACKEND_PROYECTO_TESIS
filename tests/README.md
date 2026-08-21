# Pruebas automatizadas

Estas pruebas se ejecutan contra el **sistema real**: la API por HTTP y MongoDB,
no objetos simulados.

La razón es que los fallos que ha sufrido este proyecto no eran de lógica
aislada, sino de integración:

- Un campo que Pydantic descartaba en silencio, dejando la API sin `_id`
- Evidencias que no se mostraban porque llegaban por un campo distinto al esperado
- Credenciales que se guardaban sin cifrar
- Tres umbrales de confianza distintos conviviendo en el mismo sistema

Ninguno de esos se detecta con dobles de prueba: hay que hablar con el sistema
de verdad.

## Cómo ejecutarlas

Necesitas el backend y MongoDB en marcha.

```bash
pip install pytest httpx pymongo "passlib[bcrypt]" "bcrypt==4.0.1"

pytest tests/ -v
```

Variables de entorno, con sus valores por defecto:

| Variable | Por defecto |
|---|---|
| `API_BASE` | `http://localhost:8000` |
| `MONGO_URL` | `mongodb://localhost:27017` |
| `MONGO_DB` | `sistema_armas` |
| `AGENT_TOKEN` | `TokenDePruebaLocal_2026` |

`AGENT_TOKEN` debe coincidir con el que tenga configurado el backend, o las
pruebas del agente fallarán con 401.

## Qué cubre cada archivo

| Archivo | Contenido |
|---|---|
| `test_autenticacion.py` | Inicio de sesión y control de acceso por rol |
| `test_agente.py` | El camino crítico: detección → incidente → alerta |
| `test_regresiones.py` | Fallos concretos que ya ocurrieron una vez |

## Sobre `test_regresiones.py`

Cada prueba de ese archivo corresponde a un problema real que se detectó en el
sistema, con el motivo explicado en su documentación. No están ahí por
completitud: están para que ese fallo concreto no vuelva a pasar inadvertido.

Si una falla, lee su docstring antes de tocar nada: describe qué se rompió la
vez anterior y por qué importaba.

## Advertencia

Las pruebas **escriben en la base de datos**: crean usuarios, cámaras,
incidentes y alertas. Úsalas contra un entorno de desarrollo, nunca contra la
base de producción.

Algunas incluyen esperas de 5,5 segundos para respetar el anti-avalancha del
endpoint del agente, así que la ejecución completa tarda alrededor de un minuto.
