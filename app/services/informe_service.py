"""Informe del periodo: qué vence, cómo va contra el anterior y un consejo corto."""

from sqlalchemy.orm import Session

from app.domain.bolsas import OBLIGATORIO
from app.domain.informe import Compromiso, PagoHecho, consejos, frase_periodos, gastado_de, listar_avisos
from app.models import Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import InformeOut, PeriodoCifra, RecordatorioOut
from app.services import presupuesto_service as presupuesto


def _cifra(foto) -> PeriodoCifra:
    return PeriodoCifra(
        inicio=foto.ciclo.inicio,
        fin=foto.ciclo.fin,
        ingresado=foto.ingreso_confirmado,
        gastado=gastado_de(foto),
    )


def ver(db: Session, usuario: Usuario) -> InformeOut:
    foto = presupuesto.preparar(db, usuario)
    deudas = [
        Compromiso(
            "deuda",
            deuda.id,
            deuda.nombre,
            (deuda.cuota_minima or deuda.saldo_pendiente) if deuda.tipo == "cuotas" else deuda.saldo_pendiente,
            dia=deuda.dia_de_pago,
            fecha_limite=deuda.fecha_limite if deuda.tipo == "pago_unico" else None,
        )
        for deuda in repo.deudas_de(db, usuario.id)
        if deuda.saldo_pendiente > 0
    ]
    cuentas = [
        Compromiso("cuenta", cuenta.id, cuenta.nombre, cuenta.monto, dia=cuenta.dia_del_mes)
        for cuenta in repo.cuentas_de(db, usuario.id)
    ]
    pagos = [
        PagoHecho(gasto.fecha, gasto.deuda_id, gasto.cuenta_fija_id, gasto.categoria)
        for gasto in repo.gastos_todos(db, usuario.id)
        if gasto.categoria == OBLIGATORIO
    ]
    avisos = listar_avisos(foto.calculado_en, deudas + cuentas, pagos)

    anterior = None
    gastado_anterior = None
    if repo.hay_actividad_antes(db, usuario.id, foto.ciclo.inicio):
        perfil = presupuesto.requerir_perfil(db, usuario.id)
        previo = foto.ciclo.anterior
        foto_anterior = presupuesto._dominio(db, usuario.id, perfil, previo.fin, hoy=previo.fin)
        anterior = _cifra(foto_anterior)
        gastado_anterior = anterior.gastado

    actual = _cifra(foto)
    diferencia = None if gastado_anterior is None else actual.gastado - gastado_anterior
    return InformeOut(
        recordatorios=[
            RecordatorioOut(
                tipo=aviso.tipo,
                id=aviso.id,
                nombre=aviso.nombre,
                monto=aviso.monto,
                vence=aviso.vence,
                cuando=aviso.cuando,
            )
            for aviso in avisos
        ],
        actual=actual,
        anterior=anterior,
        diferencia_gasto=diferencia,
        frase=frase_periodos(actual.gastado, gastado_anterior),
        consejos=consejos(foto, avisos, gastado_anterior),
    )
