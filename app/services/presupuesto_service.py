"""Arma la foto del periodo: arrastre, pago fijo, colchón y el motor puro."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.fechas import hoy as hoy_usuario
from app.domain.bolsas import BOLSAS, DETALLES, GASTABLES, NOMBRES
from app.domain.ciclo import ciclo_que_contiene
from app.domain.impacto import proyectar
from app.domain.motor import (
    CuentaVista,
    DeudaVista,
    GastoVisto,
    IngresoVisto,
    Presupuesto,
    calcular,
)
from app.models import Ingreso, MovimientoFondo, Perfil, SaldoApertura, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import (
    AjusteOut,
    BolsaOut,
    CicloOut,
    ColchonResumen,
    ImpactoIn,
    ImpactoOut,
    PagoFijoOut,
    PerfilOut,
    PresupuestoOut,
    ReservasOut,
    SaldoIn,
)
from app.services.reglas import reglas_de


def requerir_perfil(db: Session, usuario_id: str) -> Perfil:
    perfil = repo.perfil_de(db, usuario_id)
    if perfil is None:
        raise ValidationError(
            "Primero cuéntame cada cuánto te pagan y cuánto es.",
            codigo="sin_perfil",
        )
    return perfil


def _dominio(
    db: Session,
    usuario_id: str,
    perfil: Perfil,
    dia: date,
    *,
    excluir_gasto_id: str | None = None,
    hoy: date | None = None,
) -> Presupuesto:
    reglas = reglas_de(perfil)
    # `dia` elige el ciclo. `hoy` es el día desde el que se cuentan los que faltan.
    ciclo = ciclo_que_contiene(dia, reglas)
    dia_calculo = hoy or dia
    if dia_calculo < ciclo.inicio:
        dia_calculo = ciclo.inicio
    elif dia_calculo > ciclo.fin:
        dia_calculo = ciclo.fin
    fila = repo.apertura_de(db, usuario_id, ciclo.inicio)
    gastos = repo.gastos_entre(db, usuario_id, ciclo.inicio, ciclo.fin)
    if excluir_gasto_id:
        gastos = [g for g in gastos if g.id != excluir_gasto_id]
    return calcular(
        ciclo=ciclo,
        reglas=reglas,
        ingresos=[
            IngresoVisto(i.monto, i.fecha, i.estado == "confirmado")
            for i in repo.ingresos_entre(db, usuario_id, ciclo.inicio, ciclo.fin)
        ],
        gastos=[
            GastoVisto(g.monto, g.categoria, g.fecha, g.deuda_id, g.cuenta_fija_id)
            for g in gastos
        ],
        deudas=[
            DeudaVista(
                d.id,
                d.saldo_pendiente,
                d.tipo,
                d.cuota_minima,
                d.dia_de_pago,
                d.fecha_limite,
            )
            for d in repo.deudas_de(db, usuario_id)
        ],
        cuentas=[
            CuentaVista(c.id, c.monto, c.dia_del_mes) for c in repo.cuentas_de(db, usuario_id)
        ],
        saldo_colchon=repo.saldo_colchon(db, usuario_id),
        saldo_apertura=fila.monto if fila else 0,
        hoy=dia_calculo,
    )


def _aportes_del_ciclo(db: Session, usuario_id: str, inicio: date) -> list[MovimientoFondo]:
    consulta = (
        select(MovimientoFondo)
        .where(
            MovimientoFondo.usuario_id == usuario_id,
            MovimientoFondo.tipo == "aporte_ciclo",
            MovimientoFondo.ciclo_inicio == inicio,
        )
        .order_by(MovimientoFondo.created_at, MovimientoFondo.id)
    )
    if db.get_bind().dialect.name != "sqlite":
        consulta = consulta.with_for_update()
    return list(db.scalars(consulta))


def _dejar_aporte(
    db: Session,
    filas: list[MovimientoFondo],
    objetivo: int,
    usuario_id: str,
    foto: Presupuesto,
) -> None:
    """Una sola fila por periodo, con el monto exacto del porcentaje actual."""
    if objetivo <= 0:
        for fila in filas:
            db.delete(fila)
        db.flush()
        return
    if not filas:
        db.add(
            MovimientoFondo(
                usuario_id=usuario_id,
                tipo="aporte_ciclo",
                monto=objetivo,
                fecha=foto.calculado_en,
                ciclo_inicio=foto.ciclo.inicio,
                motivo=f"Aporte de este periodo ({foto.reglas.pct_colchon}% de tu pago)",
            )
        )
        db.flush()
        return
    principal = filas[0]
    for extra in filas[1:]:
        db.delete(extra)
    principal.monto = objetivo
    principal.motivo = f"Aporte de este periodo ({foto.reglas.pct_colchon}% de tu pago)"
    db.flush()


def _sincronizar(db: Session, usuario_id: str, foto: Presupuesto) -> None:
    """El aporte automático de este periodo queda en el porcentaje de ahora.

    Subir el colchón de 10% a 15% deja 15% del pago, no 10% más otro 15%.
    Bajarlo devuelve la diferencia. Lo que apartaste a mano no se toca.
    Si el colchón ya se usó, no se baja de cero.
    """
    objetivo = foto.aporte_colchon if foto.aporte_colchon > 0 else 0
    filas = _aportes_del_ciclo(db, usuario_id, foto.ciclo.inicio)
    ya = sum(fila.monto for fila in filas)
    if objetivo < ya:
        saldo = foto.saldo_colchon if foto.saldo_colchon > 0 else 0
        minimo = ya - saldo
        if minimo > objetivo:
            objetivo = minimo
    if not filas and objetivo > 0:
        try:
            with db.begin_nested():
                db.add(
                    MovimientoFondo(
                        usuario_id=usuario_id,
                        tipo="aporte_ciclo",
                        monto=objetivo,
                        fecha=foto.calculado_en,
                        ciclo_inicio=foto.ciclo.inicio,
                        motivo=f"Aporte de este periodo ({foto.reglas.pct_colchon}% de tu pago)",
                    )
                )
                db.flush()
        except IntegrityError:
            _dejar_aporte(
                db,
                _aportes_del_ciclo(db, usuario_id, foto.ciclo.inicio),
                objetivo,
                usuario_id,
                foto,
            )
        return
    _dejar_aporte(db, filas, objetivo, usuario_id, foto)


def _cerrar_anteriores(db: Session, usuario_id: str, perfil: Perfil, ciclo, profundidad: int = 0) -> None:
    if repo.apertura_de(db, usuario_id, ciclo.inicio):
        return
    if profundidad > 36 or not repo.hay_actividad_antes(db, usuario_id, ciclo.inicio):
        return
    anterior = ciclo.anterior
    _cerrar_anteriores(db, usuario_id, perfil, anterior, profundidad + 1)
    foto = _dominio(db, usuario_id, perfil, anterior.fin)
    _sincronizar(db, usuario_id, foto)
    db.add(
        SaldoApertura(
            usuario_id=usuario_id,
            ciclo_inicio=ciclo.inicio,
            monto=foto.disponible_para_gastar,
            origen="arrastre",
        )
    )
    db.flush()


def _asegurar_pago_fijo(db: Session, usuario_id: str, perfil: Perfil, ciclo) -> None:
    if perfil.omitir_pago_ciclo == ciclo.inicio:
        return
    pagos = [i for i in repo.ingresos_entre(db, usuario_id, ciclo.inicio, ciclo.fin) if i.es_pago_fijo]
    if not pagos:
        db.add(
            Ingreso(
                usuario_id=usuario_id,
                monto=perfil.monto_pago,
                fecha=ciclo.inicio,
                estado="esperado",
                descripcion=perfil.nombre_pago,
                es_pago_fijo=True,
            )
        )
        db.flush()
        return
    for pago in pagos:
        if pago.estado == "esperado" and pago.monto != perfil.monto_pago:
            pago.monto = perfil.monto_pago
            pago.descripcion = perfil.nombre_pago
    db.flush()


def preparar(db: Session, usuario: Usuario, dia: date | None = None) -> Presupuesto:
    dia = dia or hoy_usuario()
    perfil = requerir_perfil(db, usuario.id)
    ciclo = ciclo_que_contiene(dia, reglas_de(perfil))
    _cerrar_anteriores(db, usuario.id, perfil, ciclo)
    _asegurar_pago_fijo(db, usuario.id, perfil, ciclo)
    foto = _dominio(db, usuario.id, perfil, dia)
    _sincronizar(db, usuario.id, foto)
    foto.saldo_colchon = repo.saldo_colchon(db, usuario.id)
    return foto


def _salida(db: Session, usuario: Usuario, perfil: Perfil, foto: Presupuesto) -> PresupuestoOut:
    porcentajes = foto.reglas.porcentajes()
    bolsas = [
        BolsaOut(
            id=bolsa,
            nombre=NOMBRES[bolsa],
            detalle=DETALLES[bolsa],
            porcentaje=porcentajes[bolsa],
            asignado=foto.asignado.get(bolsa, 0),
            gastado=foto.gastado.get(bolsa, 0),
            disponible=foto.disponible.get(bolsa, 0),
        )
        for bolsa in GASTABLES
    ]
    pagos = [
        i
        for i in repo.ingresos_entre(db, usuario.id, foto.ciclo.inicio, foto.ciclo.fin)
        if i.es_pago_fijo
    ]
    pago = pagos[0] if pagos else None
    return PresupuestoOut(
        estado=foto.estado,
        frase=foto.frase,
        nombre=usuario.nombre,
        monto_pago=perfil.monto_pago,
        nombre_pago=perfil.nombre_pago,
        saldo_apertura=foto.saldo_apertura,
        ingreso_confirmado=foto.ingreso_confirmado,
        ingreso_esperado=foto.ingreso_esperado,
        disponible_para_gastar=foto.disponible_para_gastar,
        por_dia=foto.por_dia,
        faltante=foto.faltante,
        ciclo=CicloOut(
            inicio=foto.ciclo.inicio,
            fin=foto.ciclo.fin,
            dias_restantes=foto.dias_restantes,
            frecuencia=perfil.frecuencia,
            proximo_pago=foto.ciclo.fin + timedelta(days=1),
        ),
        bolsas=bolsas,
        colchon=ColchonResumen(
            saldo=foto.saldo_colchon,
            aporte_del_ciclo=foto.aporte_colchon,
            porcentaje=perfil.pct_colchon,
        ),
        reservas=ReservasOut(
            cuotas=foto.reserva_cuotas,
            cuentas=foto.reserva_cuentas,
            cuotas_pagadas=foto.cuotas_pagadas,
            cuentas_pagadas=foto.cuentas_pagadas,
        ),
        ajustes=[
            AjusteOut(bolsa=a.bolsa, nombre=NOMBRES.get(a.bolsa, a.bolsa), monto=a.monto, motivo=a.motivo)
            for a in foto.ajustes
        ],
        pago_fijo=(
            PagoFijoOut(
                id=pago.id,
                monto=pago.monto,
                fecha=pago.fecha,
                confirmado=pago.estado == "confirmado",
                nombre=pago.descripcion,
            )
            if pago
            else None
        ),
    )


def ver(db: Session, usuario: Usuario) -> PresupuestoOut:
    perfil = requerir_perfil(db, usuario.id)
    foto = preparar(db, usuario)
    return _salida(db, usuario, perfil, foto)


def impacto(db: Session, usuario: Usuario, datos: ImpactoIn) -> ImpactoOut:
    if datos.categoria not in BOLSAS:
        raise ValidationError("Esa bolsa no existe.")
    foto = preparar(db, usuario)
    visto = proyectar(foto, datos.monto, datos.categoria)
    return ImpactoOut(
        monto=visto.monto,
        categoria=visto.categoria,
        nivel=visto.nivel,
        bolsa_antes=visto.bolsa_antes,
        bolsa_despues=visto.bolsa_despues,
        total_antes=visto.total_antes,
        total_despues=visto.total_despues,
        exceso_bolsa=visto.exceso_bolsa,
        exceso_total=visto.exceso_total,
        dias_restantes=visto.dias_restantes,
        por_dia_antes=visto.por_dia_antes,
        por_dia_despues=visto.por_dia_despues,
        cubierto_por_colchon=visto.cubierto_por_colchon,
        faltante_tras_colchon=visto.faltante_tras_colchon,
        frase=visto.frase,
    )


def declarar_saldo(db: Session, usuario: Usuario, datos: SaldoIn) -> PresupuestoOut:
    """La persona dice cuánto tiene hoy. Reemplaza el arrastre de este periodo."""
    perfil = requerir_perfil(db, usuario.id)
    dia = hoy_usuario()
    ciclo = ciclo_que_contiene(dia, reglas_de(perfil))
    fila = repo.apertura_de(db, usuario.id, ciclo.inicio)
    if fila is None:
        db.add(
            SaldoApertura(
                usuario_id=usuario.id,
                ciclo_inicio=ciclo.inicio,
                monto=datos.monto,
                origen="declarado",
            )
        )
    else:
        fila.monto = datos.monto
        fila.origen = "declarado"
    db.flush()
    return ver(db, usuario)


def perfil_vista(perfil: Perfil) -> PerfilOut:
    return PerfilOut(
        frecuencia=perfil.frecuencia,
        dia_de_corte=perfil.dia_de_corte,
        segundo_dia_de_corte=perfil.segundo_dia_de_corte,
        ancla_de_pago=perfil.ancla_de_pago,
        monto_pago=perfil.monto_pago,
        nombre_pago=perfil.nombre_pago,
        pct_obligatorio=perfil.pct_obligatorio,
        pct_deuda_extra=perfil.pct_deuda_extra,
        pct_variable=perfil.pct_variable,
        pct_gustos=perfil.pct_gustos,
        pct_colchon=perfil.pct_colchon,
    )


def ciclo_de_hoy(db: Session, usuario: Usuario):
    perfil = requerir_perfil(db, usuario.id)
    return ciclo_que_contiene(hoy_usuario(), reglas_de(perfil)), perfil
