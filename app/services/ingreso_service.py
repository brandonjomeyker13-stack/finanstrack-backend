from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.fechas import hoy as hoy_usuario
from app.models import Ingreso, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import IngresoIn, IngresoOut, IngresoPatch
from app.services import presupuesto_service as presupuesto


def _salida(fila: Ingreso) -> IngresoOut:
    return IngresoOut(
        id=fila.id,
        monto=fila.monto,
        fecha=fila.fecha,
        estado=fila.estado,
        descripcion=fila.descripcion,
        es_pago_fijo=fila.es_pago_fijo,
    )


def listar(db: Session, usuario: Usuario) -> list[IngresoOut]:
    foto = presupuesto.preparar(db, usuario)
    filas = repo.ingresos_entre(db, usuario.id, foto.ciclo.inicio, foto.ciclo.fin)
    return [_salida(f) for f in filas]


def crear(db: Session, usuario: Usuario, datos: IngresoIn) -> IngresoOut:
    presupuesto.requerir_perfil(db, usuario.id)
    dia = datos.fecha or hoy_usuario()
    fila = Ingreso(
        usuario_id=usuario.id,
        monto=datos.monto,
        fecha=dia,
        estado="confirmado" if datos.confirmado else "esperado",
        descripcion=datos.descripcion.strip(),
        es_pago_fijo=False,
    )
    db.add(fila)
    db.flush()
    return _salida(fila)


def confirmar(db: Session, usuario: Usuario, ingreso_id: str, monto: int | None = None) -> IngresoOut:
    fila = repo.ingreso_de(db, usuario.id, ingreso_id)
    if fila is None:
        raise NotFoundError("No encontré ese ingreso.")
    if monto is not None and monto <= 0:
        raise ValidationError("El monto tiene que ser mayor que cero.")
    fila.estado = "confirmado"
    if monto is not None:
        fila.monto = monto
    db.flush()
    return _salida(fila)


def actualizar(db: Session, usuario: Usuario, ingreso_id: str, datos: IngresoPatch) -> IngresoOut:
    fila = repo.ingreso_de(db, usuario.id, ingreso_id)
    if fila is None:
        raise NotFoundError("No encontré ese ingreso.")
    if datos.monto is not None:
        fila.monto = datos.monto
    if datos.descripcion is not None:
        fila.descripcion = datos.descripcion.strip()
    if datos.confirmado is not None:
        fila.estado = "confirmado" if datos.confirmado else "esperado"
    db.flush()
    return _salida(fila)


def eliminar(db: Session, usuario: Usuario, ingreso_id: str) -> None:
    fila = repo.ingreso_de(db, usuario.id, ingreso_id)
    if fila is None:
        raise NotFoundError("No encontré ese ingreso.")
    db.delete(fila)
    db.flush()
