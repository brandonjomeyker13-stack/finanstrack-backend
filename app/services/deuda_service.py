from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.fechas import hoy as hoy_usuario
from app.domain.bolsas import DEUDA_EXTRA, OBLIGATORIO
from app.domain.motor import DeudaVista
from app.models import Deuda, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import AbonoIn, DeudaIn, DeudaOut, DeudaPatch, GastoIn
from app.services import gasto_service, presupuesto_service as presupuesto


def _validar(
    *,
    nombre: str,
    tipo: str,
    monto_total: int,
    saldo: int,
    cuota: int | None,
    dia: int | None,
    fecha,
    tasa: float | None,
) -> dict:
    if not nombre.strip():
        raise ValidationError("La deuda necesita un nombre.")
    if saldo < 0 or saldo > monto_total:
        raise ValidationError("El saldo no cuadra con lo que debías al principio.")
    if tasa is not None and tasa < 0:
        raise ValidationError("La tasa no puede ser negativa.")
    if tipo == "cuotas":
        if cuota is None or cuota <= 0:
            raise ValidationError("La cuota tiene que ser mayor que cero.")
        if cuota > monto_total:
            raise ValidationError("La cuota no puede ser mayor que el total.")
        if dia is None or not 1 <= dia <= 31:
            raise ValidationError("El día de pago tiene que estar entre 1 y 31.")
        return {"cuota_minima": cuota, "dia_de_pago": dia, "fecha_limite": None}
    if tipo != "pago_unico":
        raise ValidationError("Elige cuotas o un solo pago.")
    if fecha is None:
        raise ValidationError("¿Para cuándo hay que pagarla?")
    return {"cuota_minima": None, "dia_de_pago": None, "fecha_limite": fecha}


def _mejor(deudas: list[Deuda]) -> str | None:
    vivas = [d for d in deudas if d.saldo_pendiente > 0]
    if not vivas:
        return None
    def clave(d: Deuda):
        tasa = d.tasa_interes_anual if d.tasa_interes_anual is not None else -1
        return (tasa, d.saldo_pendiente)
    return max(vivas, key=clave).id


def listar(db: Session, usuario: Usuario) -> list[DeudaOut]:
    foto = presupuesto.preparar(db, usuario)
    gastos = repo.gastos_entre(db, usuario.id, foto.ciclo.inicio, foto.ciclo.fin)
    pagadas = {g.deuda_id for g in gastos if g.deuda_id and g.categoria == OBLIGATORIO}
    deudas = repo.deudas_de(db, usuario.id)
    sugerida = _mejor(deudas)
    hoy = hoy_usuario()
    salida = []
    for deuda in deudas:
        vista = DeudaVista(
            deuda.id,
            deuda.saldo_pendiente,
            deuda.tipo,
            deuda.cuota_minima,
            deuda.dia_de_pago,
            deuda.fecha_limite,
        )
        progreso = 0.0 if deuda.monto_total <= 0 else (deuda.monto_total - deuda.saldo_pendiente) / deuda.monto_total
        vencida = (
            deuda.tipo == "pago_unico"
            and deuda.saldo_pendiente > 0
            and deuda.fecha_limite is not None
            and deuda.fecha_limite < hoy
        )
        salida.append(
            DeudaOut(
                id=deuda.id,
                nombre=deuda.nombre,
                tipo=deuda.tipo,
                monto_total=deuda.monto_total,
                saldo_pendiente=deuda.saldo_pendiente,
                tasa_interes_anual=deuda.tasa_interes_anual,
                cuota_minima=deuda.cuota_minima,
                dia_de_pago=deuda.dia_de_pago,
                fecha_limite=deuda.fecha_limite,
                compromiso=vista.compromiso(foto.ciclo),
                cuota_pagada=deuda.id in pagadas,
                vencida=vencida,
                sugerida=deuda.id == sugerida,
                progreso=max(0.0, min(1.0, progreso)),
            )
        )
    return salida


def crear(db: Session, usuario: Usuario, datos: DeudaIn) -> DeudaOut:
    presupuesto.requerir_perfil(db, usuario.id)
    saldo = datos.monto_total if datos.saldo_pendiente is None else datos.saldo_pendiente
    extra = _validar(
        nombre=datos.nombre,
        tipo=datos.tipo,
        monto_total=datos.monto_total,
        saldo=saldo,
        cuota=datos.cuota_minima,
        dia=datos.dia_de_pago,
        fecha=datos.fecha_limite,
        tasa=datos.tasa_interes_anual,
    )
    fila = Deuda(
        usuario_id=usuario.id,
        nombre=datos.nombre.strip(),
        tipo=datos.tipo,
        monto_total=datos.monto_total,
        saldo_pendiente=saldo,
        tasa_interes_anual=datos.tasa_interes_anual,
        **extra,
    )
    db.add(fila)
    db.flush()
    return _por_id(db, usuario, fila.id)


def actualizar(db: Session, usuario: Usuario, deuda_id: str, datos: DeudaPatch) -> DeudaOut:
    deuda = repo.deuda_de(db, usuario.id, deuda_id)
    if deuda is None or not deuda.activa:
        raise NotFoundError("No encontré esa deuda.")
    tipo = datos.tipo or deuda.tipo
    extra = _validar(
        nombre=datos.nombre or deuda.nombre,
        tipo=tipo,
        monto_total=datos.monto_total or deuda.monto_total,
        saldo=deuda.saldo_pendiente if datos.saldo_pendiente is None else datos.saldo_pendiente,
        cuota=datos.cuota_minima if datos.cuota_minima is not None else deuda.cuota_minima,
        dia=datos.dia_de_pago if datos.dia_de_pago is not None else deuda.dia_de_pago,
        fecha=datos.fecha_limite if datos.fecha_limite is not None else deuda.fecha_limite,
        tasa=deuda.tasa_interes_anual if datos.tasa_interes_anual is None else datos.tasa_interes_anual,
    )
    deuda.nombre = (datos.nombre or deuda.nombre).strip()
    deuda.tipo = tipo
    deuda.monto_total = datos.monto_total or deuda.monto_total
    if datos.saldo_pendiente is not None:
        deuda.saldo_pendiente = datos.saldo_pendiente
    deuda.tasa_interes_anual = (
        deuda.tasa_interes_anual if datos.tasa_interes_anual is None else datos.tasa_interes_anual
    )
    deuda.cuota_minima = extra["cuota_minima"]
    deuda.dia_de_pago = extra["dia_de_pago"]
    deuda.fecha_limite = extra["fecha_limite"]
    db.flush()
    return _por_id(db, usuario, deuda.id)


def _por_id(db: Session, usuario: Usuario, deuda_id: str) -> DeudaOut:
    for fila in listar(db, usuario):
        if fila.id == deuda_id:
            return fila
    raise NotFoundError("No encontré esa deuda.")


def archivar(db: Session, usuario: Usuario, deuda_id: str) -> None:
    deuda = repo.deuda_de(db, usuario.id, deuda_id)
    if deuda is None:
        raise NotFoundError("No encontré esa deuda.")
    deuda.activa = False
    db.flush()


def abonar(db: Session, usuario: Usuario, deuda_id: str, datos: AbonoIn):
    deuda = repo.deuda_de(db, usuario.id, deuda_id)
    if deuda is None or not deuda.activa:
        raise NotFoundError("No encontré esa deuda.")
    if deuda.saldo_pendiente <= 0:
        raise ValidationError("Esa deuda ya está pagada.")
    categoria = OBLIGATORIO if datos.como_cuota or deuda.tipo == "pago_unico" else DEUDA_EXTRA
    verbo = "Pago de" if categoria == OBLIGATORIO else "Abono a"
    return gasto_service.registrar(
        db,
        usuario,
        GastoIn(
            monto=datos.monto,
            descripcion=f"{verbo} {deuda.nombre}"[:80],
            categoria=categoria,
            deuda_id=deuda.id,
            explicacion=datos.explicacion,
            origen=datos.origen,
        ),
    )
