"""La foto del periodo. Una función pura: no toca la base ni el reloj.

Los números de este producto tienen que poder probarse y repetirse.
Ninguna pantalla vuelve a calcular plata: pide esta foto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.domain.bolsas import BOLSAS, COLCHON, GASTABLES, OBLIGATORIO, ORDEN_APARTAR, ORDEN_RECORTE
from app.domain.ciclo import Ciclo, ReglasPago
from app.domain.dinero import por_dia, recortar, repartir

ESPERANDO_PAGO = "esperando_pago"
CON_LO_QUE_QUEDA = "con_lo_que_queda"
NO_ALCANZA = "no_alcanza"
PASASTE = "pasaste"
AJUSTADO = "ajustado"
EN_ORDEN = "en_orden"

FRASES = {
    ESPERANDO_PAGO: "Cuando confirmes que te llegó el pago, armamos las bolsas.",
    CON_LO_QUE_QUEDA: "En este periodo todavía no hay un pago. Estás usando lo que ya tenías.",
    NO_ALCANZA: "Tu pago no alcanza para las cuotas y las cuentas fijas.",
    PASASTE: "Ya gastaste más de lo que tenías en este periodo.",
    AJUSTADO: "Las cuotas y las cuentas fijas obligaron a achicar otras bolsas.",
    EN_ORDEN: "Este periodo va en orden.",
}


@dataclass(frozen=True)
class GastoVisto:
    monto: int
    categoria: str
    fecha: date
    deuda_id: str | None = None
    cuenta_fija_id: str | None = None

    @property
    def es_cuota(self) -> bool:
        return self.deuda_id is not None and self.categoria == OBLIGATORIO

    @property
    def es_cuenta_fija(self) -> bool:
        return self.cuenta_fija_id is not None and self.categoria == OBLIGATORIO


@dataclass(frozen=True)
class DeudaVista:
    id: str
    saldo: int
    tipo: str
    cuota: int | None
    dia_de_pago: int | None
    fecha_limite: date | None

    def compromiso(self, ciclo: Ciclo) -> int:
        if self.saldo <= 0:
            return 0
        if self.tipo == "pago_unico":
            if self.fecha_limite is None or self.fecha_limite > ciclo.fin:
                return 0
            return self.saldo
        if ciclo.es_periodo_corto and not ciclo.contiene_dia_del_mes(self.dia_de_pago or 0):
            return 0
        cuota = self.cuota or 0
        return self.saldo if cuota > self.saldo else cuota


@dataclass(frozen=True)
class CuentaVista:
    id: str
    monto: int
    dia_del_mes: int

    def compromiso(self, ciclo: Ciclo) -> int:
        if ciclo.es_periodo_corto and not ciclo.contiene_dia_del_mes(self.dia_del_mes):
            return 0
        return self.monto


@dataclass(frozen=True)
class IngresoVisto:
    monto: int
    fecha: date
    confirmado: bool


@dataclass(frozen=True)
class Ajuste:
    bolsa: str
    monto: int
    motivo: str


@dataclass
class Presupuesto:
    ciclo: Ciclo
    reglas: ReglasPago
    saldo_apertura: int
    ingreso_confirmado: int
    ingreso_esperado: int
    asignado: dict[str, int]
    gastado: dict[str, int]
    disponible: dict[str, int]
    reserva_cuotas: int
    cuotas_pagadas: int
    reserva_cuentas: int
    cuentas_pagadas: int
    aporte_colchon: int
    saldo_colchon: int
    faltante: int
    fuera_de_bolsas: int = 0
    ajustes: list[Ajuste] = field(default_factory=list)
    calculado_en: date = field(default_factory=date.today)

    @property
    def disponible_para_gastar(self) -> int:
        return (
            self.saldo_apertura
            + sum(self.disponible.get(bolsa, 0) for bolsa in GASTABLES)
            - self.fuera_de_bolsas
        )

    @property
    def dias_restantes(self) -> int:
        return self.ciclo.dias_restantes(self.calculado_en)

    @property
    def por_dia(self) -> int:
        return por_dia(self.disponible_para_gastar, self.dias_restantes)

    @property
    def estado(self) -> str:
        if self.ingreso_confirmado <= 0:
            return CON_LO_QUE_QUEDA if self.saldo_apertura > 0 else ESPERANDO_PAGO
        if self.faltante > 0:
            return NO_ALCANZA
        if self.disponible_para_gastar < 0:
            return PASASTE
        if self.ajustes:
            return AJUSTADO
        return EN_ORDEN

    @property
    def frase(self) -> str:
        return FRASES[self.estado]


def calcular(
    *,
    ciclo: Ciclo,
    reglas: ReglasPago,
    ingresos: list[IngresoVisto],
    gastos: list[GastoVisto],
    deudas: list[DeudaVista],
    cuentas: list[CuentaVista],
    saldo_colchon: int,
    saldo_apertura: int = 0,
    apartado_manual: int = 0,
    hoy: date,
) -> Presupuesto:
    ingresos_ciclo = [i for i in ingresos if ciclo.contiene(i.fecha)]
    gastos_ciclo = [g for g in gastos if ciclo.contiene(g.fecha)]

    confirmado = sum(i.monto for i in ingresos_ciclo if i.confirmado)
    esperado = sum(i.monto for i in ingresos_ciclo if not i.confirmado)

    gastado = {bolsa: 0 for bolsa in BOLSAS}
    for gasto in gastos_ciclo:
        if gasto.categoria in gastado:
            gastado[gasto.categoria] += gasto.monto

    if confirmado <= 0:
        return Presupuesto(
            ciclo=ciclo,
            reglas=reglas,
            saldo_apertura=saldo_apertura,
            ingreso_confirmado=0,
            ingreso_esperado=esperado,
            asignado={bolsa: 0 for bolsa in BOLSAS},
            gastado=gastado,
            disponible={bolsa: -gastado[bolsa] for bolsa in GASTABLES},
            reserva_cuotas=0,
            cuotas_pagadas=0,
            reserva_cuentas=0,
            cuentas_pagadas=0,
            aporte_colchon=0,
            saldo_colchon=saldo_colchon,
            faltante=0,
            fuera_de_bolsas=apartado_manual if apartado_manual > 0 else 0,
            calculado_en=hoy,
        )

    asignado = repartir(confirmado, reglas.porcentajes())

    deudas_pagadas = {g.deuda_id for g in gastos_ciclo if g.es_cuota and g.deuda_id}
    reserva_cuotas = sum(
        deuda.compromiso(ciclo) for deuda in deudas if deuda.id not in deudas_pagadas
    )
    cuotas_pagadas = sum(g.monto for g in gastos_ciclo if g.es_cuota)

    cuentas_pagadas_ids = {g.cuenta_fija_id for g in gastos_ciclo if g.es_cuenta_fija and g.cuenta_fija_id}
    reserva_cuentas = sum(
        cuenta.compromiso(ciclo) for cuenta in cuentas if cuenta.id not in cuentas_pagadas_ids
    )
    cuentas_ya = sum(g.monto for g in gastos_ciclo if g.es_cuenta_fija)

    libre: dict[str, int] = {
        bolsa: asignado.get(bolsa, 0) - gastado.get(bolsa, 0) for bolsa in GASTABLES
    }
    libre[COLCHON] = asignado.get(COLCHON, 0)
    libre[OBLIGATORIO] = libre.get(OBLIGATORIO, 0) - reserva_cuotas - reserva_cuentas

    ajustes: list[Ajuste] = []
    faltante = 0
    if libre[OBLIGATORIO] < 0:
        deficit = -libre[OBLIGATORIO]
        libre[OBLIGATORIO] = 0
        faltante, hechos = recortar(libre, deficit, ORDEN_RECORTE)
        ajustes = [
            Ajuste(
                bolsa=bolsa,
                monto=monto,
                motivo="Tus cuotas y cuentas fijas no caben en Cuentas.",
            )
            for bolsa, monto in hechos
        ]

    fuera_de_bolsas = 0
    if apartado_manual > 0:
        fuera_de_bolsas, _ = recortar(libre, apartado_manual, ORDEN_APARTAR)

    aporte = libre.get(COLCHON, 0)
    disponible = {bolsa: libre.get(bolsa, 0) for bolsa in GASTABLES}
    asignado_visto = {
        bolsa: disponible[bolsa] + gastado.get(bolsa, 0) for bolsa in GASTABLES
    }
    asignado_visto[COLCHON] = aporte

    return Presupuesto(
        ciclo=ciclo,
        reglas=reglas,
        saldo_apertura=saldo_apertura,
        ingreso_confirmado=confirmado,
        ingreso_esperado=esperado,
        asignado=asignado_visto,
        gastado=gastado,
        disponible=disponible,
        reserva_cuotas=reserva_cuotas,
        cuotas_pagadas=cuotas_pagadas,
        reserva_cuentas=reserva_cuentas,
        cuentas_pagadas=cuentas_ya,
        aporte_colchon=aporte,
        saldo_colchon=saldo_colchon,
        faltante=faltante,
        fuera_de_bolsas=fuera_de_bolsas,
        ajustes=ajustes,
        calculado_en=hoy,
    )
