"""La meta no mueve plata. Dice qué haría falta, y se corre sola si gastas lo juntado."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.dinero import pesos
from app.domain.motor import Presupuesto


@dataclass(frozen=True)
class MetaVista:
    nombre: str
    monto_objetivo: int
    monto_ahorrado: int
    aporte_por_ciclo: int
    fecha_deseada: date | None


@dataclass(frozen=True)
class Proyeccion:
    restante: int
    ciclos_al_ritmo: int | None
    fecha_estimada: date | None
    aporte_posible_hoy: int
    no_cabe_este_ciclo: bool
    llega_a_tiempo: bool | None
    aporte_para_la_fecha: int | None
    frase: str


def proyectar_meta(meta: MetaVista, presupuesto: Presupuesto) -> Proyeccion:
    restante = meta.monto_objetivo - meta.monto_ahorrado
    if restante < 0:
        restante = 0
    duracion = presupuesto.ciclo.duracion_en_dias

    if restante <= 0:
        return Proyeccion(
            restante=0,
            ciclos_al_ritmo=0,
            fecha_estimada=presupuesto.calculado_en,
            aporte_posible_hoy=0,
            no_cabe_este_ciclo=False,
            llega_a_tiempo=True,
            aporte_para_la_fecha=0,
            frase="Ya llegaste.",
        )

    margen = presupuesto.disponible_para_gastar if presupuesto.disponible_para_gastar > 0 else 0
    aporte_posible = meta.aporte_por_ciclo if meta.aporte_por_ciclo < margen else margen
    ciclos = None
    fecha = None
    if meta.aporte_por_ciclo > 0:
        ciclos = (restante + meta.aporte_por_ciclo - 1) // meta.aporte_por_ciclo
        fecha = presupuesto.ciclo.inicio + timedelta(days=duracion * ciclos)

    llega: bool | None = None
    necesario: int | None = None
    if meta.fecha_deseada is not None:
        dias = (meta.fecha_deseada - presupuesto.calculado_en).days
        ciclos_disponibles = 0 if dias <= 0 else max(1, dias // duracion)
        if ciclos_disponibles <= 0:
            necesario = restante
        else:
            necesario = (restante + ciclos_disponibles - 1) // ciclos_disponibles
        llega = ciclos is not None and ciclos_disponibles > 0 and ciclos <= ciclos_disponibles

    no_cabe = meta.aporte_por_ciclo > margen
    if ciclos is None:
        frase = "Dime cuánto quieres apartar cada pago y te digo para cuándo."
    elif no_cabe:
        frase = (
            f"Este periodo solo te alcanzaría para apartar {pesos(aporte_posible)}. "
            f"A tu ritmo serían {ciclos} pagos."
        )
    elif llega is False and necesario is not None:
        frase = (
            f"A este ritmo no llegas a la fecha. Harían falta {pesos(necesario)} por pago."
        )
    elif fecha is not None:
        frase = f"A este ritmo llegas en {ciclos} pagos."
    else:
        frase = "Sigue anotando lo que juntas."

    return Proyeccion(
        restante=restante,
        ciclos_al_ritmo=ciclos,
        fecha_estimada=fecha,
        aporte_posible_hoy=aporte_posible,
        no_cabe_este_ciclo=no_cabe,
        llega_a_tiempo=llega,
        aporte_para_la_fecha=necesario,
        frase=frase,
    )
