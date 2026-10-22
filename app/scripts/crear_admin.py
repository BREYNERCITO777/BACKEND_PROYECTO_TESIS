"""Crea el primer administrador en una instalación nueva.

El alta de usuarios (POST /users) exige ser administrador, así que en una base
de datos vacía nadie podría entrar al panel. Este script crea esa primera
cuenta directamente en MongoDB, con el mismo hash (bcrypt) que usa la API.

Uso, dentro del contenedor del backend:

    docker compose exec backend python -m app.scripts.crear_admin --email admin@municipalidad.gob.pe --nombre "Administrador"

La contraseña se pide por teclado (no queda en el historial de la terminal).
"""
import argparse
import asyncio
import getpass
import sys

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

from app.core.config import settings
from app.repositories.user_repository import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def crear(email: str, nombre: str, clave: str) -> None:
    """Inserta la cuenta de administrador; falla si el email ya existe."""
    cliente = AsyncIOMotorClient(settings.MONGO_URL)
    try:
        repo = UserRepository(cliente[settings.MONGO_DB])
        if await repo.email_exists(email):
            sys.exit(f"Ya existe una cuenta con el email {email}.")
        await repo.create(email=email, password_hash=pwd_context.hash(clave), role="admin", name=nombre)
        print(f"Administrador creado: {email}")
    finally:
        cliente.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--email", required=True)
    p.add_argument("--nombre", default="Administrador")
    args = p.parse_args()
    clave = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if len(clave) < 8:
        sys.exit("La contraseña debe tener al menos 8 caracteres.")
    if clave != getpass.getpass("Repite la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    asyncio.run(crear(args.email, args.nombre, clave))


if __name__ == "__main__":
    main()
