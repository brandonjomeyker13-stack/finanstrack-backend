"""Qué pasa si haces este gasto, antes de anotarlo.

No dice "te pasaste por 40.000". Dice cuánto te quedaría por día.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.bolsas import COLCHON
from app.domain.dinero import pesos, por_dia
from app.domain.motor import Presupuesto

CABE = "cabe"
ROMPE_BOLSA = "rompe_bolsa"
ROMPE_TOTAL = "rompe_total"


@dataclass(frozen=True)
class Impacto:
    monto: int
    categoria: str
    nivel: str
    bolsa_antes: int
    bolsa_despues: int
    total_antes: int
    total_despues: int
    exceso_bolsa: int
    exceso_total: int
    dias_restantes: int
    por_dia_antes: int
    por_dia_despues: int
    cubierto_por_colchon: int
    faltante_tras_colchon: int

    @property
    def frase(self) -> str:
        if self.categoria == COLCHON and self.faltante_tras_colchon <= 0:
            return f"Sale del colchón. Quedarían {pesos(self.bolsa_despues)} guardados."
        if self.nivel == CABE:
            return f"Cabe. Te quedarían {pesos(self.por_dia_despues)} por día."
        if self.nivel == ROMPE_BOLSA:
            return (
                "Se sale de su bolsa, pero todavía te alcanza en el total. "
                f"Te quedarían {pesos(self.por_dia_despues)} por día."
            )
        return (
            "Esto no te alcanza con lo que tienes en este periodo. "
            "Puedes anotarlo igual si cuentas de dónde sale."
        )


def _exceso(monto: int, disponible: int) -> int:
    """Si ya estás en rojo, el exceso es este gasto, no el hueco viejo más el gasto."""
    margen = disponible if disponible > 0 else 0
    sobra = monto - margen
    return sobra if sobra > 0 else 0


def proyectar(presupuesto: Presupuesto, monto: int, categoria: str) -> Impacto:
    if monto <= 0:
        monto = 0
    total_antes = presupuesto.disponible_para_gastar
    dias = presupuesto.dias_restantes

    if categoria == COLCHON:
        saldo = presupuesto.saldo_colchon if presupuesto.saldo_colchon > 0 else 0
        cubierto = monto if monto < saldo else saldo
        faltante = monto - cubierto
        total_despues = total_antes - faltante
        if faltante <= 0:
            nivel = CABE
        elif faltante > (total_antes if total_antes > 0 else 0):
            nivel = ROMPE_TOTAL
        else:
            nivel = ROMPE_BOLSA
        return Impacto(
            monto=monto,
            categoria=categoria,
            nivel=nivel,
            bolsa_antes=presupuesto.saldo_colchon,
            bolsa_despues=presupuesto.saldo_colchon - cubierto,
            total_antes=total_antes,
            total_despues=total_despues,
            exceso_bolsa=faltante,
            exceso_total=_exceso(faltante, total_antes),
            dias_restantes=dias,
            por_dia_antes=presupuesto.por_dia,
            por_dia_despues=por_dia(total_despues, dias),
            cubierto_por_colchon=cubierto,
            faltante_tras_colchon=faltante,
        )

    bolsa_antes = presupuesto.disponible.get(categoria, 0)
    bolsa_despues = bolsa_antes - monto
    total_despues = total_antes - monto
    exceso_bolsa = _exceso(monto, bolsa_antes)
    exceso_total = _exceso(monto, total_antes)
    if exceso_total > 0:
        nivel = ROMPE_TOTAL
    elif exceso_bolsa > 0:
        nivel = ROMPE_BOLSA
    else:
        nivel = CABE
    return Impacto(
        monto=monto,
        categoria=categoria,
        nivel=nivel,
        bolsa_antes=bolsa_antes,
        bolsa_despues=bolsa_despues,
        total_antes=total_antes,
        total_despues=total_despues,
        exceso_bolsa=exceso_bolsa,
        exceso_total=exceso_total,
        dias_restantes=dias,
        por_dia_antes=presupuesto.por_dia,
        por_dia_despues=por_dia(total_despues, dias),
        cubierto_por_colchon=0,
        faltante_tras_colchon=0,
    )
