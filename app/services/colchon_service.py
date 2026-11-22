from sqlalchemy.orm import Session

from app.core.fechas import hoy as hoy_usuario
from app.models import MovimientoFondo, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import AporteIn, ColchonOut, MovimientoOut
from app.services import presupuesto_service as presupuesto


def ver(db: Session, usuario: Usuario) -> ColchonOut:
    foto = presupuesto.preparar(db, usuario)
    movimientos = [
        MovimientoOut(id=m.id, tipo=m.tipo, monto=m.monto, fecha=m.fecha, motivo=m.motivo)
        for m in repo.movimientos_fondo(db, usuario.id)
    ]
    return ColchonOut(
        saldo=foto.saldo_colchon,
        aporte_del_ciclo=foto.aporte_colchon,
        movimientos=movimientos,
    )


def aportar(db: Session, usuario: Usuario, datos: AporteIn) -> ColchonOut:
    foto = presupuesto.preparar(db, usuario)
    db.add(
        MovimientoFondo(
            usuario_id=usuario.id,
            tipo="aporte_manual",
            monto=datos.monto,
            fecha=hoy_usuario(),
            ciclo_inicio=foto.ciclo.inicio,
            motivo="Lo metiste a mano",
        )
    )
    db.flush()
    return ver(db, usuario)
