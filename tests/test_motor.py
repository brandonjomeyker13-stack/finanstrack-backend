from datetime import date

from app.domain.bolsas import COLCHON, DEUDA_EXTRA, GUSTOS, OBLIGATORIO, VARIABLE
from app.domain.ciclo import MENSUAL, QUINCENAL, ReglasPago, ciclo_que_contiene
from app.domain.impacto import CABE, ROMPE_BOLSA, ROMPE_TOTAL, proyectar
from app.domain.metas import MetaVista, proyectar_meta
from app.domain.motor import (
    AJUSTADO,
    CON_LO_QUE_QUEDA,
    ESPERANDO_PAGO,
    NO_ALCANZA,
    PASASTE,
    CuentaVista,
    DeudaVista,
    GastoVisto,
    IngresoVisto,
    calcular,
)

REGLAS = ReglasPago(frecuencia=MENSUAL, dia_de_corte=1)
HOY = date(2026, 3, 1)


def _ciclo():
    return ciclo_que_contiene(HOY, REGLAS)


def _foto(**kwargs):
    base = dict(
        ciclo=_ciclo(),
        reglas=REGLAS,
        ingresos=[IngresoVisto(2_500_000, HOY, confirmado=True)],
        gastos=[],
        deudas=[],
        cuentas=[],
        saldo_colchon=0,
        saldo_apertura=0,
        hoy=HOY,
    )
    base.update(kwargs)
    return calcular(**base)


def test_el_pago_se_reparte_y_el_colchon_no_esta_para_gastar():
    foto = _foto()
    assert foto.ingreso_confirmado == 2_500_000
    assert foto.disponible_para_gastar == 2_250_000
    assert foto.aporte_colchon == 250_000
    assert foto.por_dia == 72_581
    assert foto.estado == "en_orden"
    assert sum(foto.asignado[b] for b in (OBLIGATORIO, DEUDA_EXTRA, VARIABLE, GUSTOS)) + foto.aporte_colchon == 2_500_000


def test_un_pago_esperado_no_entra_al_disponible():
    foto = _foto(ingresos=[IngresoVisto(2_500_000, HOY, confirmado=False)])
    assert foto.disponible_para_gastar == 0
    assert foto.ingreso_esperado == 2_500_000
    assert foto.estado == ESPERANDO_PAGO


def test_sin_pago_se_vive_de_lo_que_queda():
    foto = _foto(ingresos=[], saldo_apertura=80_000)
    assert foto.estado == CON_LO_QUE_QUEDA
    assert foto.disponible_para_gastar == 80_000


def test_la_cuota_se_aparta_de_cuentas_y_no_se_cobra_dos_veces():
    deuda = DeudaVista("d1", saldo=900_000, tipo="cuotas", cuota=400_000, dia_de_pago=5, fecha_limite=None)
    antes = _foto(deudas=[deuda])
    assert antes.reserva_cuotas == 400_000
    assert antes.disponible[OBLIGATORIO] == 1_125_000 - 400_000

    despues = _foto(
        deudas=[deuda],
        gastos=[GastoVisto(400_000, OBLIGATORIO, date(2026, 3, 5), deuda_id="d1")],
    )
    assert despues.reserva_cuotas == 0
    assert despues.cuotas_pagadas == 400_000
    assert despues.disponible[OBLIGATORIO] == 1_125_000 - 400_000


def test_si_la_cuota_no_cabe_se_achican_las_otras_bolsas_y_queda_dicho():
    deuda = DeudaVista("d1", 3_000_000, "cuotas", 2_000_000, 5, None)
    foto = _foto(deudas=[deuda])
    assert foto.estado == AJUSTADO
    assert foto.faltante == 0
    assert foto.disponible[GUSTOS] == 0
    assert foto.disponible[DEUDA_EXTRA] == 0
    assert foto.aporte_colchon == 0
    assert foto.disponible[VARIABLE] == 500_000
    assert foto.disponible_para_gastar == 500_000
    assert {a.bolsa for a in foto.ajustes} == {GUSTOS, DEUDA_EXTRA, COLCHON}


def test_si_ni_recortando_alcanza_hay_faltante():
    deuda = DeudaVista("d1", 5_000_000, "cuotas", 2_600_000, 5, None)
    foto = _foto(deudas=[deuda])
    assert foto.estado == NO_ALCANZA
    assert foto.faltante == 100_000


def test_la_cuota_de_una_quincena_no_pesa_en_la_otra():
    reglas = ReglasPago(frecuencia=QUINCENAL, dia_de_corte=15, segundo_dia_de_corte=30)
    deuda = DeudaVista("d1", 500_000, "cuotas", 100_000, 15, None)
    ingreso = [IngresoVisto(1_000_000, date(2026, 3, 15), True)]
    donde_cae = calcular(
        ciclo=ciclo_que_contiene(date(2026, 3, 16), reglas),
        reglas=reglas,
        ingresos=ingreso,
        gastos=[],
        deudas=[deuda],
        cuentas=[],
        saldo_colchon=0,
        hoy=date(2026, 3, 16),
    )
    la_otra = calcular(
        ciclo=ciclo_que_contiene(date(2026, 3, 30), reglas),
        reglas=reglas,
        ingresos=[IngresoVisto(1_000_000, date(2026, 3, 30), True)],
        gastos=[],
        deudas=[deuda],
        cuentas=[],
        saldo_colchon=0,
        hoy=date(2026, 3, 30),
    )
    assert donde_cae.reserva_cuotas == 100_000
    assert la_otra.reserva_cuotas == 0


def test_una_deuda_de_una_sola_vez_solo_aprieta_en_su_fecha():
    lejos = DeudaVista("d1", 120_000, "pago_unico", None, None, date(2026, 6, 1))
    este_mes = DeudaVista("d2", 120_000, "pago_unico", None, None, date(2026, 3, 20))
    foto = _foto(deudas=[lejos, este_mes])
    assert foto.reserva_cuotas == 120_000


def test_la_cuenta_fija_se_aparta_y_al_pagarla_no_se_duplica():
    cuenta = CuentaVista("c1", 800_000, 5)
    antes = _foto(cuentas=[cuenta])
    assert antes.reserva_cuentas == 800_000
    despues = _foto(
        cuentas=[cuenta],
        gastos=[GastoVisto(800_000, OBLIGATORIO, date(2026, 3, 5), cuenta_fija_id="c1")],
    )
    assert despues.reserva_cuentas == 0
    assert despues.disponible[OBLIGATORIO] == 1_125_000 - 800_000


def test_pasarse_deja_el_disponible_en_rojo():
    foto = _foto(gastos=[GastoVisto(3_000_000, VARIABLE, HOY)])
    assert foto.estado == PASASTE
    assert foto.disponible_para_gastar < 0


def test_el_aviso_acota_el_exceso_al_gasto_nuevo():
    foto = _foto(gastos=[GastoVisto(3_000_000, VARIABLE, HOY)])
    impacto = proyectar(foto, 20_000, VARIABLE)
    assert impacto.nivel == ROMPE_TOTAL
    assert impacto.exceso_total == 20_000


def test_un_gasto_que_cabe_dice_cuanto_queda_por_dia():
    impacto = proyectar(_foto(), 31_000, VARIABLE)
    assert impacto.nivel == CABE
    assert impacto.por_dia_despues < impacto.por_dia_antes


def test_romperse_la_bolsa_no_es_lo_mismo_que_no_alcanzar():
    impacto = proyectar(_foto(), 600_000, GUSTOS)
    assert impacto.nivel == ROMPE_BOLSA
    assert impacto.total_despues > 0


def test_el_colchon_absorbe_el_golpe_si_tiene_con_que():
    foto = _foto(saldo_colchon=300_000)
    impacto = proyectar(foto, 80_000, COLCHON)
    assert impacto.nivel == CABE
    assert impacto.cubierto_por_colchon == 80_000
    assert impacto.total_despues == foto.disponible_para_gastar


def test_la_meta_avisa_si_el_aporte_no_cabe():
    foto = _foto(gastos=[GastoVisto(2_200_000, VARIABLE, HOY)])
    proy = proyectar_meta(
        MetaVista("La moto", 1_000_000, 0, 200_000, None),
        foto,
    )
    assert proy.no_cabe_este_ciclo
    assert proy.ciclos_al_ritmo == 5
