from datetime import date

from app.domain.informe import Compromiso, PagoHecho, listar_avisos, proximo_dia


HOY = date(2026, 11, 22)


def test_el_dia_5_cuando_hoy_es_22_cae_el_mes_siguiente():
    assert proximo_dia(HOY, 5) == date(2026, 12, 5)


def test_avisa_el_dia_anterior_y_no_repite_si_ya_se_pago():
    celular = Compromiso("deuda", "d1", "Celular", 100_000, dia=23)
    avisos = listar_avisos(HOY, [celular], [])
    assert len(avisos) == 1
    assert avisos[0].cuando == "manana"
    assert avisos[0].vence == date(2026, 11, 23)

    pagado = PagoHecho(date(2026, 11, 23), "d1", None, "obligatorio")
    assert listar_avisos(HOY, [celular], [pagado]) == []


def test_un_vencimiento_lejano_no_interrumpe():
    arriendo = Compromiso("cuenta", "c1", "Arriendo", 800_000, dia=5)
    assert listar_avisos(HOY, [arriendo], []) == []


def test_hoy_y_vencido_siguen_visibles():
    hoy = Compromiso("cuenta", "c1", "Luz", 90_000, dia=22)
    vencida = Compromiso("deuda", "d2", "Préstamo", 50_000, fecha_limite=date(2026, 11, 20))
    avisos = listar_avisos(HOY, [hoy, vencida], [])
    assert [aviso.cuando for aviso in avisos] == ["vencido", "hoy"]
