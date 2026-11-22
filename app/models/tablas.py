from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


def _id() -> str:
    return str(uuid4())


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nombre: Mapped[str] = mapped_column(String(80))
    # Identificador estable de Google. Vacío si la cuenta se creó con contraseña
    # y todavía no se ha abierto con Google.
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)


class Perfil(Base, TimestampMixin):
    """Un pago fijo, en una fecha exacta, y cómo se reparte."""

    __tablename__ = "perfiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, index=True
    )
    frecuencia: Mapped[str] = mapped_column(String(20))
    dia_de_corte: Mapped[int] = mapped_column(Integer)
    segundo_dia_de_corte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ancla_de_pago: Mapped[date | None] = mapped_column(Date, nullable=True)
    monto_pago: Mapped[int] = mapped_column(BigInteger)
    nombre_pago: Mapped[str] = mapped_column(String(80), default="Mi pago")
    pct_obligatorio: Mapped[int] = mapped_column(Integer, default=45)
    pct_deuda_extra: Mapped[int] = mapped_column(Integer, default=15)
    pct_variable: Mapped[int] = mapped_column(Integer, default=20)
    pct_gustos: Mapped[int] = mapped_column(Integer, default=10)
    pct_colchon: Mapped[int] = mapped_column(Integer, default=10)
    # Si este periodo arrancó con "ya gasté una parte", no se inventa el pago:
    # el disponible es lo que la persona dijo que le queda.
    omitir_pago_ciclo: Mapped[date | None] = mapped_column(Date, nullable=True)


class Ingreso(Base, TimestampMixin):
    __tablename__ = "ingresos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    monto: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    estado: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(80))
    es_pago_fijo: Mapped[bool] = mapped_column(Boolean, default=False)


class Deuda(Base, TimestampMixin):
    __tablename__ = "deudas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(20))
    monto_total: Mapped[int] = mapped_column(BigInteger)
    saldo_pendiente: Mapped[int] = mapped_column(BigInteger)
    tasa_interes_anual: Mapped[float | None] = mapped_column(Float, nullable=True)
    cuota_minima: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dia_de_pago: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class CuentaFija(Base, TimestampMixin):
    __tablename__ = "cuentas_fijas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    monto: Mapped[int] = mapped_column(BigInteger)
    dia_del_mes: Mapped[int] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Gasto(Base, TimestampMixin):
    __tablename__ = "gastos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    monto: Mapped[int] = mapped_column(BigInteger)
    descripcion: Mapped[str] = mapped_column(String(80))
    categoria: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    origen: Mapped[str] = mapped_column(String(20), default="normal")
    nivel_alerta: Mapped[str] = mapped_column(String(20), default="ninguna")
    explicacion: Mapped[str | None] = mapped_column(String(280), nullable=True)
    deuda_id: Mapped[str | None] = mapped_column(
        ForeignKey("deudas.id", ondelete="SET NULL"), nullable=True
    )
    cuenta_fija_id: Mapped[str | None] = mapped_column(
        ForeignKey("cuentas_fijas.id", ondelete="SET NULL"), nullable=True
    )


class MovimientoFondo(Base, TimestampMixin):
    __tablename__ = "movimientos_fondo"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    monto: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date)
    ciclo_inicio: Mapped[date] = mapped_column(Date, index=True)
    gasto_id: Mapped[str | None] = mapped_column(
        ForeignKey("gastos.id", ondelete="SET NULL"), nullable=True
    )
    motivo: Mapped[str] = mapped_column(String(160))


class Meta(Base, TimestampMixin):
    __tablename__ = "metas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    monto_objetivo: Mapped[int] = mapped_column(BigInteger)
    monto_ahorrado: Mapped[int] = mapped_column(BigInteger, default=0)
    aporte_por_ciclo: Mapped[int] = mapped_column(BigInteger, default=0)
    fecha_deseada: Mapped[date | None] = mapped_column(Date, nullable=True)
    archivada: Mapped[bool] = mapped_column(Boolean, default=False)


class SaldoApertura(Base, TimestampMixin):
    __tablename__ = "saldos_apertura"
    __table_args__ = (UniqueConstraint("usuario_id", "ciclo_inicio", name="uq_apertura_ciclo"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    ciclo_inicio: Mapped[date] = mapped_column(Date)
    monto: Mapped[int] = mapped_column(BigInteger)
    origen: Mapped[str] = mapped_column(String(20))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)
