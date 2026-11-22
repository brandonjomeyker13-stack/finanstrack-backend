from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.bolsas import OBLIGATORIO
from app.domain.motor import CuentaVista
from app.models import CuentaFija, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import CuentaIn, CuentaOut, CuentaPatch, GastoIn, PagoCuentaIn
from app.services import gasto_service, presupuesto_service as presupuesto


def listar(db: Session, usuario: Usuario) -> list[CuentaOut]:
    foto = presupuesto.preparar(db, usuario)
    gastos = repo.gastos_entre(db, usuario.id, foto.ciclo.inicio, foto.ciclo.fin)
    pagadas = {g.cuenta_fija_id for g in gastos if g.cuenta_fija_id and g.categoria == OBLIGATORIO}
    salida = []
    for cuenta in repo.cuentas_de(db, usuario.id):
        vista = CuentaVista(cuenta.id, cuenta.monto, cuenta.dia_del_mes)
        salida.append(
            CuentaOut(
                id=cuenta.id,
                nombre=cuenta.nombre,
                monto=cuenta.monto,
                dia_del_mes=cuenta.dia_del_mes,
                compromiso=vista.compromiso(foto.ciclo),
                pagada=cuenta.id in pagadas,
            )
        )
    return salida


def crear(db: Session, usuario: Usuario, datos: CuentaIn) -> CuentaOut:
    presupuesto.requerir_perfil(db, usuario.id)
    if not datos.nombre.strip():
        raise ValidationError("La cuenta necesita un nombre.")
    fila = CuentaFija(
        usuario_id=usuario.id,
        nombre=datos.nombre.strip(),
        monto=datos.monto,
        dia_del_mes=datos.dia_del_mes,
    )
    db.add(fila)
    db.flush()
    for item in listar(db, usuario):
        if item.id == fila.id:
            return item
    raise NotFoundError("No encontré esa cuenta.")


def actualizar(db: Session, usuario: Usuario, cuenta_id: str, datos: CuentaPatch) -> CuentaOut:
    cuenta = repo.cuenta_de(db, usuario.id, cuenta_id)
    if cuenta is None or not cuenta.activa:
        raise NotFoundError("No encontré esa cuenta.")
    if datos.nombre is not None:
        cuenta.nombre = datos.nombre.strip()
    if datos.monto is not None:
        cuenta.monto = datos.monto
    if datos.dia_del_mes is not None:
        cuenta.dia_del_mes = datos.dia_del_mes
    db.flush()
    for item in listar(db, usuario):
        if item.id == cuenta.id:
            return item
    raise NotFoundError("No encontré esa cuenta.")


def archivar(db: Session, usuario: Usuario, cuenta_id: str) -> None:
    cuenta = repo.cuenta_de(db, usuario.id, cuenta_id)
    if cuenta is None:
        raise NotFoundError("No encontré esa cuenta.")
    cuenta.activa = False
    db.flush()


def pagar(db: Session, usuario: Usuario, cuenta_id: str, datos: PagoCuentaIn):
    cuenta = repo.cuenta_de(db, usuario.id, cuenta_id)
    if cuenta is None or not cuenta.activa:
        raise NotFoundError("No encontré esa cuenta.")
    return gasto_service.registrar(
        db,
        usuario,
        GastoIn(
            monto=datos.monto or cuenta.monto,
            descripcion=cuenta.nombre,
            categoria=OBLIGATORIO,
            cuenta_fija_id=cuenta.id,
            explicacion=datos.explicacion,
            origen=datos.origen,
        ),
    )
