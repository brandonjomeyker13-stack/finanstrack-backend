from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.auth import BorrarCuentaIn, GoogleIn, LoginIn, RefreshIn, RegistroIn, TokenOut, UsuarioOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def registro(datos: RegistroIn, db: Session = Depends(get_db)):
    return auth_service.registrar(db, datos)


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    return auth_service.entrar(db, datos)


@router.post("/google", response_model=TokenOut)
def google(datos: GoogleIn, db: Session = Depends(get_db)):
    """Entra con Google. Si el correo no tiene cuenta, la crea."""
    return auth_service.entrar_con_google(db, datos.credential)


@router.post("/refresh", response_model=TokenOut)
def refresh(datos: RefreshIn, db: Session = Depends(get_db)):
    return auth_service.refrescar(db, datos.refresh_token)


@router.post("/cerrar-sesion", status_code=status.HTTP_204_NO_CONTENT)
def cerrar(datos: RefreshIn, db: Session = Depends(get_db)):
    auth_service.cerrar(db, datos.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return auth_service.yo(db, usuario)


@router.delete("/cuenta", status_code=status.HTTP_204_NO_CONTENT)
def borrar_cuenta(
    datos: BorrarCuentaIn,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Borra a la persona y sus periodos, gastos, deudas y sesión."""
    auth_service.eliminar_cuenta(db, usuario, datos.confirmacion)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
