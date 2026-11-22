import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import google_id
from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import Usuario
from app.repositories import consultas as repo
from app.schemas.auth import LoginIn, RegistroIn, TokenOut, UsuarioOut


def _vista(db: Session, usuario: Usuario) -> UsuarioOut:
    perfil = repo.perfil_de(db, usuario.id)
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        onboarding_completo=perfil is not None,
    )


def _emitir(db: Session, usuario: Usuario) -> TokenOut:
    crudo = generate_refresh_token()
    expira = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    repo.guardar_refresh(db, usuario.id, hash_token(crudo), expira)
    return TokenOut(
        access_token=create_access_token(usuario.id),
        refresh_token=crudo,
        usuario=_vista(db, usuario),
    )


def registrar(db: Session, datos: RegistroIn) -> TokenOut:
    email = datos.email.lower().strip()
    if repo.usuario_por_email(db, email):
        raise ConflictError("Ya hay una cuenta con ese correo.")
    usuario = Usuario(
        email=email,
        nombre=datos.nombre.strip(),
        password_hash=hash_password(datos.password),
    )
    db.add(usuario)
    db.flush()
    return _emitir(db, usuario)


def entrar(db: Session, datos: LoginIn) -> TokenOut:
    email = datos.email.lower().strip()
    usuario = repo.usuario_por_email(db, email)
    if usuario is None or not verify_password(datos.password, usuario.password_hash):
        if usuario is not None and usuario.google_sub:
            raise UnauthorizedError("La contraseña no coincide. Esta cuenta entra con Google.")
        raise UnauthorizedError("Correo o contraseña incorrectos.")
    return _emitir(db, usuario)


def _nombre_de_google(datos: dict, email: str) -> str:
    crudo = datos.get("name") or datos.get("given_name") or email.split("@", 1)[0]
    nombre = " ".join(str(crudo).split())
    return (nombre or "Tu cuenta")[:80]


def entrar_con_google(db: Session, credential: str) -> TokenOut:
    client_id = settings.GOOGLE_CLIENT_ID.strip()
    if not client_id:
        raise ValidationError(
            "Falta GOOGLE_CLIENT_ID en el servidor.",
            codigo="google_sin_configurar",
        )
    datos = google_id.verificar_id_token(credential, client_id)
    sub = str(datos["sub"])
    email = str(datos["email"]).lower().strip()

    por_google = repo.usuario_por_google(db, sub)
    if por_google is not None:
        return _emitir(db, por_google)

    usuario = repo.usuario_por_email(db, email)
    if usuario is None:
        usuario = Usuario(
            email=email,
            nombre=_nombre_de_google(datos, email),
            # Nadie inicia con contraseña: es un hash de un secreto que no se guarda.
            password_hash=hash_password(secrets.token_urlsafe(48)),
            google_sub=sub,
        )
        db.add(usuario)
        db.flush()
        return _emitir(db, usuario)

    if usuario.google_sub and usuario.google_sub != sub:
        raise ConflictError("Ese correo ya está en otra cuenta de Google.")
    usuario.google_sub = sub
    db.flush()
    return _emitir(db, usuario)


def refrescar(db: Session, crudo: str) -> TokenOut:
    guardado = repo.refresh_por_hash(db, hash_token(crudo))
    if guardado is None or guardado.revocado:
        raise UnauthorizedError("Tu sesión venció. Vuelve a entrar.")
    expira = guardado.expira
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < datetime.now(timezone.utc):
        raise UnauthorizedError("Tu sesión venció. Vuelve a entrar.")
    usuario = repo.usuario_por_id(db, guardado.usuario_id)
    if usuario is None:
        raise UnauthorizedError("Tu sesión venció. Vuelve a entrar.")
    return TokenOut(
        access_token=create_access_token(usuario.id),
        refresh_token=crudo,
        usuario=_vista(db, usuario),
    )


def cerrar(db: Session, crudo: str) -> None:
    guardado = repo.refresh_por_hash(db, hash_token(crudo))
    if guardado is not None:
        guardado.revocado = True


def yo(db: Session, usuario: Usuario) -> UsuarioOut:
    return _vista(db, usuario)


def eliminar_cuenta(db: Session, usuario: Usuario, confirmacion: str) -> None:
    if confirmacion.strip().upper() != "BORRAR":
        raise ValidationError("Para borrar la cuenta hay que confirmarlo.")
    repo.borrar_cuenta(db, usuario.id)
