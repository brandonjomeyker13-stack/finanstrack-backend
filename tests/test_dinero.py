from app.domain.bolsas import ORDEN_RECORTE
from app.domain.dinero import por_dia, recortar, repartir


def test_el_reparto_suma_el_pago_exacto():
    partes = repartir(2_500_000, {
        "obligatorio": 45,
        "deuda_extra": 15,
        "variable": 20,
        "gustos": 10,
        "colchon": 10,
    })
    assert sum(partes.values()) == 2_500_000
    assert partes["obligatorio"] == 1_125_000
    assert partes["deuda_extra"] == 375_000
    assert partes["variable"] == 500_000
    assert partes["gustos"] == 250_000
    assert partes["colchon"] == 250_000


def test_el_resto_de_un_peso_no_se_pierde():
    partes = repartir(100, {"a": 33, "b": 33, "c": 34})
    assert sum(partes.values()) == 100


def test_recortar_no_deja_negativos_y_dice_el_faltante():
    bolsas = {"gustos": 100, "deuda_extra": 50, "colchon": 0, "variable": 80}
    faltante, hechos = recortar(bolsas, 200, ORDEN_RECORTE)
    assert faltante == 0
    assert bolsas["gustos"] == 0
    assert bolsas["deuda_extra"] == 0
    assert bolsas["colchon"] == 0
    assert bolsas["variable"] == 30
    assert hechos[0] == ("gustos", 100)


def test_por_dia_redondea_sin_centavos():
    assert por_dia(2_250_000, 31) == 72_581
    assert por_dia(0, 10) == 0
    assert por_dia(-5, 3) == 0
