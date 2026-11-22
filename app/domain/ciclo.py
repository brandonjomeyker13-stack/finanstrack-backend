"""El periodo va de un pago al siguiente, no del 1 al 30.

Alguien que cobra el 15 y ve el presupuesto reiniciarse el día 1 recibe
números que no son los suyos: le quedan quince días de gastos con la
bolsa en cero, o estrena bolsa llena sin haber cobrado.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from app.core.exceptions import ValidationError

MENSUAL = "mensual"
QUINCENAL = "quincenal"
CATORCENAL = "catorcenal"
FRECUENCIAS = (MENSUAL, QUINCENAL, CATORCENAL)

MINIMO_ENTRE_QUINCENAS = 10
MAXIMO_ENTRE_QUINCENAS = 20


def _ultimo_dia(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def dia_en_mes(anio: int, mes: int, dia: int) -> date:
    """Un corte el 31 en febrero es el 28 (o el 29). "El último día"."""
    while mes < 1:
        mes += 12
        anio -= 1
    while mes > 12:
        mes -= 12
        anio += 1
    ultimo = _ultimo_dia(anio, mes)
    return date(anio, mes, dia if dia < ultimo else ultimo)


def _validar_dia(dia: int) -> None:
    if dia < 1 or dia > 31:
        raise ValidationError("El día de pago tiene que estar entre 1 y 31.")


@dataclass(frozen=True)
class ReglasPago:
    """Cómo y cuánto le pagan. El monto es fijo; la fecha es exacta."""

    frecuencia: str
    dia_de_corte: int
    segundo_dia_de_corte: int | None = None
    ancla_de_pago: date | None = None
    pct_obligatorio: int = 45
    pct_deuda_extra: int = 15
    pct_variable: int = 20
    pct_gustos: int = 10
    pct_colchon: int = 10

    def __post_init__(self) -> None:
        if self.frecuencia not in FRECUENCIAS:
            raise ValidationError("Elige cada mes, cada quincena o cada 14 días.")
        _validar_dia(self.dia_de_corte)
        if self.frecuencia == QUINCENAL:
            segundo = self.segundo_dia_de_corte
            if segundo is None:
                raise ValidationError("Falta el día de tu segunda quincena.")
            _validar_dia(segundo)
            separacion = segundo - self.dia_de_corte
            if separacion < MINIMO_ENTRE_QUINCENAS or separacion > MAXIMO_ENTRE_QUINCENAS:
                raise ValidationError(
                    "Los dos pagos tienen que estar separados entre "
                    f"{MINIMO_ENTRE_QUINCENAS} y {MAXIMO_ENTRE_QUINCENAS} días, "
                    "como el 15 y el 30."
                )
        if self.frecuencia == CATORCENAL and self.ancla_de_pago is None:
            raise ValidationError("Falta el día de tu último pago.")
        for porcentaje in self.porcentajes().values():
            if porcentaje < 0:
                raise ValidationError("Ningún porcentaje puede ser negativo.")
        if sum(self.porcentajes().values()) != 100:
            raise ValidationError(
                f"Tus porcentajes suman {sum(self.porcentajes().values())}%. "
                "Tienen que sumar 100."
            )

    def porcentajes(self) -> dict[str, int]:
        return {
            "obligatorio": self.pct_obligatorio,
            "deuda_extra": self.pct_deuda_extra,
            "variable": self.pct_variable,
            "gustos": self.pct_gustos,
            "colchon": self.pct_colchon,
        }

    @property
    def dias_de_corte(self) -> tuple[int, ...]:
        if self.frecuencia == CATORCENAL:
            return ()
        if self.frecuencia == QUINCENAL:
            return tuple(sorted({self.dia_de_corte, self.segundo_dia_de_corte or 0}))
        return (self.dia_de_corte,)


@dataclass(frozen=True)
class Ciclo:
    inicio: date
    fin: date
    dias_de_corte: tuple[int, ...] = ()
    ancla: date | None = None

    @property
    def es_catorcena(self) -> bool:
        return self.ancla is not None

    @property
    def duracion_en_dias(self) -> int:
        return (self.fin - self.inicio).days + 1

    @property
    def es_periodo_corto(self) -> bool:
        """Quincena o catorcena: un compromiso mensual pesa una sola vez."""
        return self.duracion_en_dias < 20

    def contiene(self, fecha: date) -> bool:
        return self.inicio <= fecha <= self.fin

    def contiene_dia_del_mes(self, dia: int) -> bool:
        if dia < 1 or dia > 31:
            return False
        meses = {(self.inicio.year, self.inicio.month), (self.fin.year, self.fin.month)}
        for anio, mes in meses:
            if self.contiene(dia_en_mes(anio, mes, dia)):
                return True
        return False

    def dias_restantes(self, hoy: date) -> int:
        """Nunca cero: este número divide lo que puedes gastar por día."""
        if hoy > self.fin:
            return 1
        if hoy < self.inicio:
            return self.duracion_en_dias
        restantes = (self.fin - hoy).days + 1
        return restantes if restantes >= 1 else 1

    @property
    def anterior(self) -> Ciclo:
        return ciclo_que_contiene(self.inicio - timedelta(days=1), self._reglas_minimas())

    @property
    def siguiente(self) -> Ciclo:
        return ciclo_que_contiene(self.fin + timedelta(days=1), self._reglas_minimas())

    def _reglas_minimas(self) -> ReglasPago:
        if self.es_catorcena:
            return ReglasPago(
                frecuencia=CATORCENAL,
                dia_de_corte=self.ancla.day if self.ancla else 1,
                ancla_de_pago=self.ancla,
            )
        if len(self.dias_de_corte) >= 2:
            primero, segundo = self.dias_de_corte[0], self.dias_de_corte[1]
            return ReglasPago(
                frecuencia=QUINCENAL,
                dia_de_corte=primero,
                segundo_dia_de_corte=segundo,
            )
        return ReglasPago(frecuencia=MENSUAL, dia_de_corte=self.dias_de_corte[0])


def ciclo_que_contiene(fecha: date, reglas: ReglasPago) -> Ciclo:
    if reglas.frecuencia == CATORCENAL:
        return _catorcena(fecha, reglas.ancla_de_pago or fecha)
    return _por_cortes(fecha, reglas.dias_de_corte)


def _por_cortes(fecha: date, dias: tuple[int, ...]) -> Ciclo:
    cortes: set[date] = set()
    for desfase in (-1, 0, 1):
        mes = fecha.month + desfase
        anio = fecha.year
        while mes < 1:
            mes += 12
            anio -= 1
        while mes > 12:
            mes -= 12
            anio += 1
        for dia in dias:
            cortes.add(dia_en_mes(anio, mes, dia))
    ordenados = sorted(cortes)
    inicio = max(corte for corte in ordenados if corte <= fecha)
    siguiente = min(corte for corte in ordenados if corte > inicio)
    return Ciclo(
        inicio=inicio,
        fin=siguiente - timedelta(days=1),
        dias_de_corte=tuple(sorted(dias)),
    )


def _catorcena(fecha: date, ancla: date) -> Ciclo:
    pasos = (fecha - ancla).days // 14
    inicio = ancla + timedelta(days=pasos * 14)
    return Ciclo(
        inicio=inicio,
        fin=inicio + timedelta(days=13),
        ancla=ancla,
    )
