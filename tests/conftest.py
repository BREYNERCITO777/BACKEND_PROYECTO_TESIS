"""Configuración común de las pruebas.

Las pruebas se ejecutan contra el sistema REAL —la API por HTTP y MongoDB—,
no contra objetos simulados. La razón es que los fallos que ha sufrido este
proyecto no eran de lógica aislada sino de integración: campos que Pydantic
descartaba en silencio, evidencias que no se mostraban porque llegaban por otro
campo, credenciales que no se descifraban. Nada de eso lo detecta una prueba
con dobles.

Uso:
    docker compose up -d          # o levantar backend y Mongo a mano
    pytest tests/ -v

Variables de entorno:
    API_BASE     por defecto http://localhost:8000
    MONGO_URL    por defecto mongodb://localhost:27017
    AGENT_TOKEN  debe coincidir con el del backend
"""
import os

import httpx
import pytest
from pymongo import MongoClient

API = os.environ.get("API_BASE", "http://localhost:8000")
PREFIJO = "/api/v1"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "sistema_armas")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "TokenDePruebaLocal_2026")

ADMIN = ("admin@example.com", "Admin123!")
OPERADOR = ("operador@example.com", "Oper123!")


@pytest.fixture(scope="session")
def db():
    return MongoClient(MONGO_URL)[MONGO_DB]


@pytest.fixture(scope="session")
def cliente():
    with httpx.Client(base_url=API, timeout=60.0) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def usuarios(db):
    """Crea un admin y un operador conocidos antes de nada.

    Se usan dominios reales: '.local' es un TLD reservado y EmailStr lo rechaza
    al serializar, lo que hace fallar GET /users con un 500 desconcertante.
    """
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db["users"].delete_many({"email": {"$in": [ADMIN[0], OPERADOR[0]]}})
    db["users"].insert_many([
        {"name": "Admin Pruebas", "email": ADMIN[0],
         "password_hash": pwd.hash(ADMIN[1]), "role": "admin", "estado": 1},
        {"name": "Operador Pruebas", "email": OPERADOR[0],
         "password_hash": pwd.hash(OPERADOR[1]), "role": "operator", "estado": 1},
    ])
    yield


def _entrar(cliente, credenciales):
    r = cliente.post(f"{PREFIJO}/auth/login",
                     data={"username": credenciales[0], "password": credenciales[1]})
    assert r.status_code == 200, f"No se pudo entrar como {credenciales[0]}: {r.text}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="session")
def admin(cliente, usuarios):
    return _entrar(cliente, ADMIN)


@pytest.fixture(scope="session")
def operador(cliente, usuarios):
    return _entrar(cliente, OPERADOR)


@pytest.fixture(scope="session")
def agente():
    return {"Authorization": f"Bearer {AGENT_TOKEN}"}
