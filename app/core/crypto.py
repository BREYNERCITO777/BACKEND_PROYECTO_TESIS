from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


# Prefijo propio para distinguir un valor cifrado por nosotros de uno en texto
# plano. Sin esta marca no habria forma fiable de saber si un documento viene
# de antes de que existiera el cifrado.
_MARCA = "enc:v1:"


def _clave() -> bytes:
    """
    Deriva la clave de Fernet a partir del secreto configurado.

    Fernet exige 32 bytes en base64 urlsafe; el secreto del .env es texto
    libre, asi que se pasa por SHA-256 para obtener siempre esa longitud.

    Si no se define RTSP_SECRET_KEY se usa JWT_SECRET, que ya es obligatorio.
    Asi el cifrado no obliga a configurar otra variable, pero se puede separar
    con una clave propia cuando convenga rotar una sin tocar la otra.
    """
    secreto = settings.RTSP_SECRET_KEY.strip() or settings.JWT_SECRET
    digest = hashlib.sha256(secreto.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def cifrar(texto: Optional[str]) -> Optional[str]:
    """Cifra un valor. Si ya venia cifrado, lo devuelve tal cual."""
    if not texto:
        return texto
    if texto.startswith(_MARCA):
        return texto

    token = Fernet(_clave()).encrypt(texto.encode("utf-8")).decode("ascii")
    return _MARCA + token


def descifrar(valor: Optional[str]) -> Optional[str]:
    """
    Descifra un valor.

    Los documentos anteriores al cifrado guardan la URL en texto plano y no
    llevan la marca: se devuelven sin tocar, para no romper lo que ya existe.
    """
    if not valor or not valor.startswith(_MARCA):
        return valor

    try:
        return Fernet(_clave()).decrypt(valor[len(_MARCA):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Clave equivocada o dato corrupto. Se avisa en vez de fallar en
        # silencio, porque significa que esa camara no se podra transmitir.
        return None


def huella(texto: Optional[str]) -> Optional[str]:
    """
    Huella estable de un valor, para poder mantener un indice unico sobre algo
    que se guarda cifrado.

    Hace falta porque Fernet no es determinista: cifrar dos veces la misma URL
    produce resultados distintos, asi que un indice unico sobre el texto
    cifrado nunca detectaria un duplicado.
    """
    if not texto:
        return None
    return hashlib.sha256(texto.strip().encode("utf-8")).hexdigest()


def enmascarar(url: Optional[str]) -> Optional[str]:
    """
    Oculta usuario y clave de una URL para poder mostrarla sin exponerlas.
    rtsp://ois:clave@10.0.0.1:554/x  ->  rtsp://***:***@10.0.0.1:554/x
    """
    if not url or "@" not in url:
        return url

    esquema, _, resto = url.partition("://")
    if not resto:
        return url

    credenciales, _, servidor = resto.partition("@")
    if ":" not in credenciales:
        return url

    return f"{esquema}://***:***@{servidor}"
