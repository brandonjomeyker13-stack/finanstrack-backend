from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.fechas import hoy as hoy_usuario
from app.domain.dinero import pesos
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
        puedes_meter=foto.disponible_para_gastar if foto.disponible_para_gastar > 0 else 0,
        movimientos=movimientos,
    )


def aportar(db: Session, usuario: Usuario, datos: AporteIn) -> ColchonOut:
    foto = presupuesto.preparar(db, usuario)
    espacio = foto.disponible_para_gastar if foto.disponible_para_gastar > 0 else 0
    if datos.monto > espacio:
        if espacio <= 0:
            raise ValidationError(
                "En este periodo no te queda plata para meter al colchón.",
                codigo="no_alcanza",
            )
        raise ValidationError(
            f"Solo puedes meter {pesos(espacio)}. Es lo que te queda para gastar.",
            codigo="no_alcanza",
        )
    db.add(
        MovimientoFondo(
            usuario_id=usuario.id,
            tipo="aporte_extra",
            monto=datos.monto,
            fecha=hoy_usuario(),
            ciclo_inicio=foto.ciclo.inicio,
            motivo="Lo metiste a mano",
        )
    )
    db.flush()
    return ver(db, usuario)
