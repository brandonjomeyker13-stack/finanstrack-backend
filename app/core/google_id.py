"""Confirma el ID token que entrega el botón de Google en el front.

No usa el client secret: el token se firma con las claves públicas de Google
y aquí solo se comprueba la firma, la audiencia y que el correo esté verificado.
"""

from functools import lru_cache

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.core.exceptions import UnauthorizedError

_CERTS = "https://www.googleapis.com/oauth2/v3/certs"


@lru_cache
def _claves() -> PyJWKClient:
    return PyJWKClient(_CERTS)


def verificar_id_token(token: str, client_id: str) -> dict:
    try:
        firma = _claves().get_signing_key_from_jwt(token)
        datos = jwt.decode(
            token,
            firma.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=["accounts.google.com", "https://accounts.google.com"],
        )
    except PyJWTError:
        raise UnauthorizedError("Google no reconoció esa sesión.") from None
    except Exception:
        raise UnauthorizedError("No pude confirmar la cuenta de Google.") from None

    email = datos.get("email")
    sub = datos.get("sub")
    if not isinstance(email, str) or not email.strip() or not isinstance(sub, str) or not sub:
        raise UnauthorizedError("Google no entregó el correo.")
    if datos.get("email_verified") is not True:
        raise UnauthorizedError("Ese correo de Google no está verificado.")
    return datos
