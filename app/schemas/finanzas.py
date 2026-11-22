from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Frecuencia = Literal["mensual", "quincenal", "catorcenal"]
Categoria = Literal["obligatorio", "deuda_extra", "variable", "gustos", "colchon"]
Situacion = Literal["lo_espero", "ya_llego", "me_queda"]
OrigenExtra = Literal["ingreso_extra", "ahorro", "prestamo", "desconocido"]
TipoDeuda = Literal["cuotas", "pago_unico"]


class OnboardingIn(BaseModel):
    frecuencia: Frecuencia
    dia_de_corte: int = Field(ge=1, le=31)
    segundo_dia_de_corte: int | None = Field(default=None, ge=1, le=31)
    ancla_de_pago: date | None = None
    monto_pago: int = Field(gt=0, le=999_999_999_999)
    nombre_pago: str = Field(default="Mi pago", min_length=1, max_length=80)
    situacion: Situacion
    me_queda: int | None = Field(default=None, ge=0, le=999_999_999_999)
    colchon_inicial: int = Field(default=0, ge=0, le=999_999_999_999)
    nombre: str | None = Field(default=None, max_length=80)


class PerfilIn(BaseModel):
    frecuencia: Frecuencia
    dia_de_corte: int = Field(ge=1, le=31)
    segundo_dia_de_corte: int | None = Field(default=None, ge=1, le=31)
    ancla_de_pago: date | None = None
    monto_pago: int = Field(gt=0, le=999_999_999_999)
    nombre_pago: str = Field(min_length=1, max_length=80)
    pct_obligatorio: int = Field(ge=0, le=100)
    pct_deuda_extra: int = Field(ge=0, le=100)
    pct_variable: int = Field(ge=0, le=100)
    pct_gustos: int = Field(ge=0, le=100)
    pct_colchon: int = Field(ge=0, le=100)


class PerfilOut(BaseModel):
    frecuencia: str
    dia_de_corte: int
    segundo_dia_de_corte: int | None
    ancla_de_pago: date | None
    monto_pago: int
    nombre_pago: str
    pct_obligatorio: int
    pct_deuda_extra: int
    pct_variable: int
    pct_gustos: int
    pct_colchon: int


class BolsaOut(BaseModel):
    id: str
    nombre: str
    detalle: str
    porcentaje: int
    asignado: int
    gastado: int
    disponible: int


class AjusteOut(BaseModel):
    bolsa: str
    nombre: str
    monto: int
    motivo: str


class PagoFijoOut(BaseModel):
    id: str
    monto: int
    fecha: date
    confirmado: bool
    nombre: str


class ColchonResumen(BaseModel):
    saldo: int
    aporte_del_ciclo: int
    porcentaje: int


class ReservasOut(BaseModel):
    cuotas: int
    cuentas: int
    cuotas_pagadas: int
    cuentas_pagadas: int


class CicloOut(BaseModel):
    inicio: date
    fin: date
    dias_restantes: int
    frecuencia: str
    proximo_pago: date


class PresupuestoOut(BaseModel):
    estado: str
    frase: str
    nombre: str
    monto_pago: int
    nombre_pago: str
    saldo_apertura: int
    ingreso_confirmado: int
    ingreso_esperado: int
    disponible_para_gastar: int
    por_dia: int
    faltante: int
    ciclo: CicloOut
    bolsas: list[BolsaOut]
    colchon: ColchonResumen
    reservas: ReservasOut
    ajustes: list[AjusteOut]
    pago_fijo: PagoFijoOut | None


class ImpactoIn(BaseModel):
    monto: int = Field(gt=0, le=999_999_999_999)
    categoria: Categoria


class ImpactoOut(BaseModel):
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
    frase: str


class SaldoIn(BaseModel):
    monto: int = Field(ge=0, le=999_999_999_999)


class IngresoIn(BaseModel):
    monto: int = Field(gt=0, le=999_999_999_999)
    descripcion: str = Field(min_length=1, max_length=80)
    fecha: date | None = None
    confirmado: bool = True


class IngresoPatch(BaseModel):
    monto: int | None = Field(default=None, gt=0, le=999_999_999_999)
    descripcion: str | None = Field(default=None, min_length=1, max_length=80)
    confirmado: bool | None = None


class IngresoOut(BaseModel):
    id: str
    monto: int
    fecha: date
    estado: str
    descripcion: str
    es_pago_fijo: bool


class GastoIn(BaseModel):
    monto: int = Field(gt=0, le=999_999_999_999)
    descripcion: str = Field(min_length=1, max_length=80)
    categoria: Categoria
    fecha: date | None = None
    deuda_id: str | None = None
    cuenta_fija_id: str | None = None
    explicacion: str | None = Field(default=None, max_length=280)
    origen: OrigenExtra | None = None


class GastoOut(BaseModel):
    id: str
    monto: int
    descripcion: str
    categoria: str
    fecha: date
    origen: str
    nivel_alerta: str
    explicacion: str | None
    deuda_id: str | None
    cuenta_fija_id: str | None
    frase: str | None = None


class DeudaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    tipo: TipoDeuda
    monto_total: int = Field(gt=0, le=999_999_999_999)
    saldo_pendiente: int | None = Field(default=None, ge=0, le=999_999_999_999)
    cuota_minima: int | None = Field(default=None, gt=0, le=999_999_999_999)
    dia_de_pago: int | None = Field(default=None, ge=1, le=31)
    fecha_limite: date | None = None
    tasa_interes_anual: float | None = Field(default=None, ge=0, le=500)


class DeudaPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    monto_total: int | None = Field(default=None, gt=0, le=999_999_999_999)
    saldo_pendiente: int | None = Field(default=None, ge=0, le=999_999_999_999)
    cuota_minima: int | None = Field(default=None, gt=0)
    dia_de_pago: int | None = Field(default=None, ge=1, le=31)
    fecha_limite: date | None = None
    tasa_interes_anual: float | None = Field(default=None, ge=0, le=500)
    tipo: TipoDeuda | None = None


class DeudaOut(BaseModel):
    id: str
    nombre: str
    tipo: str
    monto_total: int
    saldo_pendiente: int
    tasa_interes_anual: float | None
    cuota_minima: int | None
    dia_de_pago: int | None
    fecha_limite: date | None
    compromiso: int
    cuota_pagada: bool
    vencida: bool
    sugerida: bool
    progreso: float


class AbonoIn(BaseModel):
    monto: int = Field(gt=0, le=999_999_999_999)
    como_cuota: bool = False
    explicacion: str | None = Field(default=None, max_length=280)
    origen: OrigenExtra | None = None


class CuentaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    monto: int = Field(gt=0, le=999_999_999_999)
    dia_del_mes: int = Field(ge=1, le=31)


class CuentaPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    monto: int | None = Field(default=None, gt=0, le=999_999_999_999)
    dia_del_mes: int | None = Field(default=None, ge=1, le=31)


class CuentaOut(BaseModel):
    id: str
    nombre: str
    monto: int
    dia_del_mes: int
    compromiso: int
    pagada: bool


class PagoCuentaIn(BaseModel):
    monto: int | None = Field(default=None, gt=0, le=999_999_999_999)
    explicacion: str | None = Field(default=None, max_length=280)
    origen: OrigenExtra | None = None


class MovimientoOut(BaseModel):
    id: str
    tipo: str
    monto: int
    fecha: date
    motivo: str


class ColchonOut(BaseModel):
    saldo: int
    aporte_del_ciclo: int
    movimientos: list[MovimientoOut]


class AporteIn(BaseModel):
    monto: int = Field(gt=0, le=999_999_999_999)


class MetaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    monto_objetivo: int = Field(gt=0, le=999_999_999_999)
    monto_ahorrado: int = Field(default=0, ge=0, le=999_999_999_999)
    aporte_por_ciclo: int = Field(default=0, ge=0, le=999_999_999_999)
    fecha_deseada: date | None = None


class MetaPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    monto_objetivo: int | None = Field(default=None, gt=0)
    monto_ahorrado: int | None = Field(default=None, ge=0)
    aporte_por_ciclo: int | None = Field(default=None, ge=0)
    fecha_deseada: date | None = None
    quitar_fecha: bool = False


class MetaOut(BaseModel):
    id: str
    nombre: str
    monto_objetivo: int
    monto_ahorrado: int
    aporte_por_ciclo: int
    fecha_deseada: date | None
    restante: int
    ciclos_al_ritmo: int | None
    fecha_estimada: date | None
    aporte_posible_hoy: int
    no_cabe_este_ciclo: bool
    llega_a_tiempo: bool | None
    aporte_para_la_fecha: int | None
    frase: str
    progreso: float


class RecordatorioOut(BaseModel):
    tipo: str
    id: str
    nombre: str
    monto: int
    vence: date
    cuando: str


class PeriodoCifra(BaseModel):
    inicio: date
    fin: date
    ingresado: int
    gastado: int


class InformeOut(BaseModel):
    recordatorios: list[RecordatorioOut]
    actual: PeriodoCifra
    anterior: PeriodoCifra | None
    diferencia_gasto: int | None
    frase: str
    consejos: list[str]
