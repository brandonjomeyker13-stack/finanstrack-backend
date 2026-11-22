"""Avisos, comparación de periodos y consejos. Sin red y sin modelo de lenguaje.

Un recordatorio aparece como tarde el día anterior al vencimiento, y sigue
visible el día del pago y unos días después si nadie lo marcó como pagado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.bolsas import GASTABLES
from app.domain.ciclo import dia_en_mes
from app.domain.dinero import pesos
from app.domain.motor import EN_ORDEN, NO_ALCANZA, PASASTE, Presupuesto

_VENTANA_VENCIDO = 7


@dataclass(frozen=True)
class Compromiso:
    tipo: str
    id: str
    nombre: str
    monto: int
    dia: int | None = None
    fecha_limite: date | None = None


@dataclass(frozen=True)
class PagoHecho:
    fecha: date
    deuda_id: str | None
    cuenta_id: str | None
    categoria: str


@dataclass(frozen=True)
class Aviso:
    tipo: str
    id: str
    nombre: str
    monto: int
    vence: date
    cuando: str


def proximo_dia(hoy: date, dia: int) -> date:
    """El próximo corte de ese día del mes, o el de este mes si aún cuenta."""
    este = dia_en_mes(hoy.year, hoy.month, dia)
    if este >= hoy - timedelta(days=_VENTANA_VENCIDO):
        return este
    mes = hoy.month + 1
    anio = hoy.year
    if mes > 12:
        mes = 1
        anio += 1
    return dia_en_mes(anio, mes, dia)


def _cuando(hoy: date, vence: date) -> str | None:
    delta = (vence - hoy).days
    if delta == 1:
        return "manana"
    if delta == 0:
        return "hoy"
    if -_VENTANA_VENCIDO <= delta < 0:
        return "vencido"
    return None


def _ya_pagado(pago: PagoHecho, compromiso: Compromiso, vence: date) -> bool:
    if pago.categoria != "obligatorio":
        return False
    if abs((pago.fecha - vence).days) > _VENTANA_VENCIDO:
        return False
    if compromiso.tipo == "deuda":
        return pago.deuda_id == compromiso.id
    return pago.cuenta_id == compromiso.id


def listar_avisos(hoy: date, compromisos: list[Compromiso], pagos: list[PagoHecho]) -> list[Aviso]:
    avisos: list[Aviso] = []
    for item in compromisos:
        if item.monto <= 0:
            continue
        if item.fecha_limite is not None:
            vence = item.fecha_limite
        elif item.dia is not None:
            vence = proximo_dia(hoy, item.dia)
        else:
            continue
        cuando = _cuando(hoy, vence)
        if cuando is None:
            continue
        if any(_ya_pagado(pago, item, vence) for pago in pagos):
            continue
        avisos.append(
            Aviso(
                tipo=item.tipo,
                id=item.id,
                nombre=item.nombre,
                monto=item.monto,
                vence=vence,
                cuando=cuando,
            )
        )
    orden = {"vencido": 0, "hoy": 1, "manana": 2}
    return sorted(avisos, key=lambda aviso: (orden[aviso.cuando], aviso.vence, aviso.nombre))


def gastado_de(foto: Presupuesto) -> int:
    return sum(foto.gastado.get(bolsa, 0) for bolsa in GASTABLES)


def frase_periodos(gastado_actual: int, gastado_anterior: int | None) -> str:
    if gastado_anterior is None:
        return "Este es tu primer periodo. La comparación aparece cuando cierre."
    diferencia = gastado_actual - gastado_anterior
    if diferencia == 0:
        return "Vas gastando lo mismo que en el periodo pasado."
    if diferencia > 0:
        return f"Llevas {pesos(diferencia)} más gastados que en el periodo pasado."
    return f"Llevas {pesos(-diferencia)} menos gastados que en el periodo pasado."


def consejos(
    foto: Presupuesto,
    avisos: list[Aviso],
    gastado_anterior: int | None,
) -> list[str]:
    frases: list[str] = []
    if foto.estado == PASASTE:
        frases.append("Te pasaste de lo que podías gastar. Lo que sigue sale del colchón o del próximo pago.")
    elif foto.estado == NO_ALCANZA:
        frases.append("Las cuentas de este periodo no caben en el pago. Recorta gustos o aplaza algo.")
    if avisos:
        primero = avisos[0]
        if primero.cuando == "manana":
            frases.append(f"Mañana vence {primero.nombre}. Márcalo pagado en Plan para no contarlo dos veces.")
        elif primero.cuando == "hoy":
            frases.append(f"Hoy vence {primero.nombre}. Si ya lo pagaste, anótalo en Plan.")
        else:
            frases.append(f"{primero.nombre} venció y sigue pendiente. Anótalo o se sigue apartando.")
    elif gastado_anterior is not None and gastado_de(foto) > gastado_anterior:
        frases.append("Vas más rápido que el periodo pasado. Revisa día a día antes del siguiente gasto.")
    elif foto.estado == EN_ORDEN:
        frases.append("Vas dentro de lo apartado. No hace falta mover nada.")
    return frases[:3]
