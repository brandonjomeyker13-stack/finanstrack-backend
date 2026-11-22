"""Consultas. No deciden nada: el servicio pide, esto lee o escribe filas."""

from datetime import date, datetime

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    CuentaFija,
    Deuda,
    Gasto,
    Ingreso,
    Meta,
    MovimientoFondo,
    Perfil,
    RefreshToken,
    SaldoApertura,
    Usuario,
)


def usuario_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email))


def usuario_por_google(db: Session, google_sub: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.google_sub == google_sub))


def usuario_por_id(db: Session, usuario_id: str) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def perfil_de(db: Session, usuario_id: str) -> Perfil | None:
    return db.scalar(select(Perfil).where(Perfil.usuario_id == usuario_id))


def ingresos_entre(db: Session, usuario_id: str, inicio: date, fin: date) -> list[Ingreso]:
    return list(
        db.scalars(
            select(Ingreso)
            .where(Ingreso.usuario_id == usuario_id, Ingreso.fecha >= inicio, Ingreso.fecha <= fin)
            .order_by(Ingreso.fecha, Ingreso.created_at)
        )
    )


def ingreso_de(db: Session, usuario_id: str, ingreso_id: str) -> Ingreso | None:
    return db.scalar(select(Ingreso).where(Ingreso.id == ingreso_id, Ingreso.usuario_id == usuario_id))


def gastos_entre(db: Session, usuario_id: str, inicio: date, fin: date) -> list[Gasto]:
    return list(
        db.scalars(
            select(Gasto)
            .where(Gasto.usuario_id == usuario_id, Gasto.fecha >= inicio, Gasto.fecha <= fin)
            .order_by(Gasto.fecha.desc(), Gasto.created_at.desc())
        )
    )


def gastos_todos(db: Session, usuario_id: str) -> list[Gasto]:
    return list(
        db.scalars(
            select(Gasto)
            .where(Gasto.usuario_id == usuario_id)
            .order_by(Gasto.fecha.desc(), Gasto.created_at.desc())
        )
    )


def gasto_de(db: Session, usuario_id: str, gasto_id: str) -> Gasto | None:
    return db.scalar(select(Gasto).where(Gasto.id == gasto_id, Gasto.usuario_id == usuario_id))


def deudas_de(db: Session, usuario_id: str, solo_activas: bool = True) -> list[Deuda]:
    q = select(Deuda).where(Deuda.usuario_id == usuario_id)
    if solo_activas:
        q = q.where(Deuda.activa.is_(True))
    return list(db.scalars(q.order_by(Deuda.created_at)))


def deuda_de(db: Session, usuario_id: str, deuda_id: str) -> Deuda | None:
    return db.scalar(select(Deuda).where(Deuda.id == deuda_id, Deuda.usuario_id == usuario_id))


def cuentas_de(db: Session, usuario_id: str, solo_activas: bool = True) -> list[CuentaFija]:
    q = select(CuentaFija).where(CuentaFija.usuario_id == usuario_id)
    if solo_activas:
        q = q.where(CuentaFija.activa.is_(True))
    return list(db.scalars(q.order_by(CuentaFija.dia_del_mes)))


def cuenta_de(db: Session, usuario_id: str, cuenta_id: str) -> CuentaFija | None:
    return db.scalar(
        select(CuentaFija).where(CuentaFija.id == cuenta_id, CuentaFija.usuario_id == usuario_id)
    )


def saldo_colchon(db: Session, usuario_id: str) -> int:
    signo = case(
        (MovimientoFondo.tipo == "retiro", -MovimientoFondo.monto),
        else_=MovimientoFondo.monto,
    )
    total = db.scalar(
        select(func.coalesce(func.sum(signo), 0)).where(MovimientoFondo.usuario_id == usuario_id)
    )
    return int(total or 0)


def aporte_del_ciclo(db: Session, usuario_id: str, ciclo_inicio: date) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(MovimientoFondo.monto), 0)).where(
            MovimientoFondo.usuario_id == usuario_id,
            MovimientoFondo.tipo == "aporte_ciclo",
            MovimientoFondo.ciclo_inicio == ciclo_inicio,
        )
    )
    return int(total or 0)


def movimientos_fondo(db: Session, usuario_id: str) -> list[MovimientoFondo]:
    return list(
        db.scalars(
            select(MovimientoFondo)
            .where(MovimientoFondo.usuario_id == usuario_id)
            .order_by(MovimientoFondo.fecha.desc(), MovimientoFondo.created_at.desc())
        )
    )


def borrar_retiros_del_gasto(db: Session, gasto_id: str) -> None:
    filas = db.scalars(select(MovimientoFondo).where(MovimientoFondo.gasto_id == gasto_id))
    for fila in filas:
        db.delete(fila)


def metas_de(db: Session, usuario_id: str) -> list[Meta]:
    return list(
        db.scalars(
            select(Meta)
            .where(Meta.usuario_id == usuario_id, Meta.archivada.is_(False))
            .order_by(Meta.created_at)
        )
    )


def meta_de(db: Session, usuario_id: str, meta_id: str) -> Meta | None:
    return db.scalar(select(Meta).where(Meta.id == meta_id, Meta.usuario_id == usuario_id))


def apertura_de(db: Session, usuario_id: str, ciclo_inicio: date) -> SaldoApertura | None:
    return db.scalar(
        select(SaldoApertura).where(
            SaldoApertura.usuario_id == usuario_id,
            SaldoApertura.ciclo_inicio == ciclo_inicio,
        )
    )


def hay_actividad_antes(db: Session, usuario_id: str, dia: date) -> bool:
    consultas = (
        select(Ingreso.id).where(Ingreso.usuario_id == usuario_id, Ingreso.fecha < dia),
        select(Gasto.id).where(Gasto.usuario_id == usuario_id, Gasto.fecha < dia),
        select(SaldoApertura.id).where(
            SaldoApertura.usuario_id == usuario_id, SaldoApertura.ciclo_inicio < dia
        ),
        select(MovimientoFondo.id).where(
            MovimientoFondo.usuario_id == usuario_id, MovimientoFondo.fecha < dia
        ),
    )
    return any(db.scalar(q.limit(1)) is not None for q in consultas)


def borrar_pagos_fijos_esperados(db: Session, usuario_id: str) -> None:
    filas = db.scalars(
        select(Ingreso).where(
            Ingreso.usuario_id == usuario_id,
            Ingreso.es_pago_fijo.is_(True),
            Ingreso.estado == "esperado",
        )
    )
    for fila in filas:
        db.delete(fila)


def refresh_por_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))


def revocar_refresh_del_usuario(db: Session, usuario_id: str) -> None:
    filas = db.scalars(select(RefreshToken).where(RefreshToken.usuario_id == usuario_id))
    for fila in filas:
        fila.revocado = True


def guardar_refresh(db: Session, usuario_id: str, token_hash: str, expira: datetime) -> None:
    db.add(RefreshToken(usuario_id=usuario_id, token_hash=token_hash, expira=expira))


def borrar_cuenta(db: Session, usuario_id: str) -> None:
    """Borra a la persona y todo lo que colgaba de ella.

    El orden importa: un gasto apunta a una deuda, y un movimiento del
    colchón apunta a un gasto. Primero se sueltan esas puntas.
    """
    for modelo in (
        MovimientoFondo,
        Gasto,
        Ingreso,
        Deuda,
        CuentaFija,
        Meta,
        SaldoApertura,
        Perfil,
        RefreshToken,
    ):
        db.execute(delete(modelo).where(modelo.usuario_id == usuario_id))
    db.execute(delete(Usuario).where(Usuario.id == usuario_id))
