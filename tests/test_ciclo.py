from datetime import date

from app.domain.ciclo import CATORCENAL, MENSUAL, QUINCENAL, ReglasPago, ciclo_que_contiene


def test_el_corte_31_en_febrero_es_el_ultimo_dia():
    reglas = ReglasPago(frecuencia=MENSUAL, dia_de_corte=31)
    ciclo = ciclo_que_contiene(date(2026, 2, 10), reglas)
    assert ciclo.inicio == date(2026, 1, 31)
    assert ciclo.fin == date(2026, 2, 27)
    siguiente = ciclo.siguiente
    assert siguiente.inicio == date(2026, 2, 28)
    assert siguiente.fin == date(2026, 3, 30)


def test_quincena_15_y_30_son_dos_periodos():
    reglas = ReglasPago(frecuencia=QUINCENAL, dia_de_corte=15, segundo_dia_de_corte=30)
    primera = ciclo_que_contiene(date(2026, 3, 15), reglas)
    segunda = ciclo_que_contiene(date(2026, 3, 30), reglas)
    assert primera.inicio == date(2026, 3, 15)
    assert primera.fin == date(2026, 3, 29)
    assert segunda.inicio == date(2026, 3, 30)
    assert segunda.fin == date(2026, 4, 14)
    assert primera.siguiente.inicio == segunda.inicio
    assert primera.es_periodo_corto


def test_catorcena_anclada_a_un_sabado():
    ancla = date(2026, 1, 3)
    reglas = ReglasPago(frecuencia=CATORCENAL, dia_de_corte=3, ancla_de_pago=ancla)
    ciclo = ciclo_que_contiene(date(2026, 1, 20), reglas)
    assert ciclo.inicio == date(2026, 1, 17)
    assert ciclo.fin == date(2026, 1, 30)
    assert ciclo.duracion_en_dias == 14
    assert ciclo.anterior.fin == date(2026, 1, 16)
    assert ciclo.siguiente.inicio == date(2026, 1, 31)


def test_el_31_pesa_en_la_quincena_donde_cae_el_dia():
    reglas = ReglasPago(frecuencia=QUINCENAL, dia_de_corte=1, segundo_dia_de_corte=16)
    primera = ciclo_que_contiene(date(2026, 3, 5), reglas)
    assert primera.inicio == date(2026, 3, 1)
    assert primera.fin == date(2026, 3, 15)
    assert primera.contiene_dia_del_mes(5)
    assert not primera.contiene_dia_del_mes(31)
    segunda = ciclo_que_contiene(date(2026, 3, 20), reglas)
    assert segunda.contiene_dia_del_mes(31)
