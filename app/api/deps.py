from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Usuario
from app.repositories import consultas as repo

_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    credencial: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credencial is None or not credencial.credentials:
        raise UnauthorizedError("Entra para continuar.")
    try:
        payload = decode_access_token(credencial.credentials)
    except InvalidTokenError:
        raise UnauthorizedError("Tu sesión venció. Vuelve a entrar.") from None
    usuario_id = payload.get("sub")
    usuario = repo.usuario_por_id(db, usuario_id) if isinstance(usuario_id, str) else None
    if usuario is None:
        raise UnauthorizedError("Tu sesión venció. Vuelve a entrar.")
    return usuario
