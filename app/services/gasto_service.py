"""Anotar, corregir y borrar un gasto, con lo que le hace a la deuda y al colchón.

Corregir revierte primero. Si no, borrar un abono dejaría la deuda bajada
para siempre, y borrar un imprevisto dejaría el retiro del colchón vivo.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.fechas import hoy as hoy_usuario
from app.domain.bolsas import BOLSAS, COLCHON, DEUDA_EXTRA, OBLIGATORIO
from app.domain.impacto import ROMPE_TOTAL, proyectar
from app.models import Gasto, MovimientoFondo, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import GastoIn, GastoOut
from app.services import presupuesto_service as presupuesto


def _fecha(valor: date | None) -> date:
    dia = valor or hoy_usuario()
    if dia > hoy_usuario():
        raise ValidationError("Ese día todavía no llega.")
    return dia


def _nivel(impacto_nivel: str) -> str:
    if impacto_nivel == "rompe_total":
        return "rompe_total"
    if impacto_nivel == "rompe_bolsa":
        return "rompe_bolsa"
    return "ninguna"


def _mover_deuda(db: Session, usuario_id: str, deuda_id: str | None, cambio: int) -> None:
    if not deuda_id:
        return
    deuda = repo.deuda_de(db, usuario_id, deuda_id)
    if deuda is None:
        return
    nuevo = deuda.saldo_pendiente + cambio
    if nuevo < 0:
        nuevo = 0
    if nuevo > deuda.monto_total:
        nuevo = deuda.monto_total
    deuda.saldo_pendiente = nuevo


def _revertir(db: Session, usuario_id: str, gasto: Gasto) -> None:
    repo.borrar_retiros_del_gasto(db, gasto.id)
    _mover_deuda(db, usuario_id, gasto.deuda_id, gasto.monto)


def _aplicar(db: Session, usuario: Usuario, gasto: Gasto, cubierto: int, ciclo_inicio: date) -> None:
    if cubierto > 0:
        db.add(
            MovimientoFondo(
                usuario_id=usuario.id,
                tipo="retiro",
                monto=cubierto,
                fecha=gasto.fecha,
                ciclo_inicio=ciclo_inicio,
                gasto_id=gasto.id,
                motivo=f"Imprevisto: {gasto.descripcion}",
            )
        )
    _mover_deuda(db, usuario.id, gasto.deuda_id, -gasto.monto)


def _validar_vinculos(db: Session, usuario_id: str, datos: GastoIn) -> None:
    if datos.categoria not in BOLSAS:
        raise ValidationError("Esa bolsa no existe.")
    if datos.deuda_id and datos.cuenta_fija_id:
        raise ValidationError("Un gasto no puede ser una deuda y una cuenta fija a la vez.")
    if datos.deuda_id and datos.categoria not in (OBLIGATORIO, DEUDA_EXTRA):
        raise ValidationError("El pago de una deuda va en Cuentas o en Deudas.")
    if datos.cuenta_fija_id and datos.categoria != OBLIGATORIO:
        raise ValidationError("El pago de una cuenta fija va en Cuentas.")
    if datos.deuda_id and repo.deuda_de(db, usuario_id, datos.deuda_id) is None:
        raise NotFoundError("No encontré esa deuda.")
    if datos.cuenta_fija_id and repo.cuenta_de(db, usuario_id, datos.cuenta_fija_id) is None:
        raise NotFoundError("No encontré esa cuenta.")


def _explicacion(datos: GastoIn, nivel: str) -> tuple[str, str | None]:
    texto = _limpio(datos.explicacion)
    if nivel == ROMPE_TOTAL:
        if not texto:
            raise ValidationError(
                "Esto no te alcanza. Cuéntame de dónde sale la plata, o bájale al monto.",
                codigo="falta_explicacion",
            )
        if datos.categoria == COLCHON:
            return "colchon", texto
        return datos.origen or "desconocido", texto
    if datos.categoria == COLCHON:
        return "colchon", texto
    return "normal", texto


def _limpio(texto: str | None) -> str | None:
    if texto is None:
        return None
    limpio = texto.strip()
    return limpio or None


def _salida(gasto: Gasto, frase: str | None = None) -> GastoOut:
    return GastoOut(
        id=gasto.id,
        monto=gasto.monto,
        descripcion=gasto.descripcion,
        categoria=gasto.categoria,
        fecha=gasto.fecha,
        origen=gasto.origen,
        nivel_alerta=gasto.nivel_alerta,
        explicacion=gasto.explicacion,
        deuda_id=gasto.deuda_id,
        cuenta_fija_id=gasto.cuenta_fija_id,
        frase=frase,
    )


def _foto_del_gasto(db: Session, usuario: Usuario, dia: date, excluir: str | None = None):
    foto_hoy = presupuesto.preparar(db, usuario)
    if foto_hoy.ciclo.contiene(dia) and excluir is None:
        return foto_hoy
    perfil = presupuesto.requerir_perfil(db, usuario.id)
    return presupuesto._dominio(
        db,
        usuario.id,
        perfil,
        dia,
        excluir_gasto_id=excluir,
        hoy=hoy_usuario(),
    )


def registrar(db: Session, usuario: Usuario, datos: GastoIn) -> GastoOut:
    _validar_vinculos(db, usuario.id, datos)
    dia = _fecha(datos.fecha)
    foto = _foto_del_gasto(db, usuario, dia)
    visto = proyectar(foto, datos.monto, datos.categoria)
    origen, explicacion = _explicacion(datos, visto.nivel)
    gasto = Gasto(
        usuario_id=usuario.id,
        monto=datos.monto,
        descripcion=datos.descripcion.strip(),
        categoria=datos.categoria,
        fecha=dia,
        origen=origen,
        nivel_alerta=_nivel(visto.nivel),
        explicacion=explicacion,
        deuda_id=datos.deuda_id,
        cuenta_fija_id=datos.cuenta_fija_id,
    )
    db.add(gasto)
    db.flush()
    _aplicar(db, usuario, gasto, visto.cubierto_por_colchon, foto.ciclo.inicio)
    db.flush()
    return _salida(gasto, visto.frase)


def corregir(db: Session, usuario: Usuario, gasto_id: str, datos: GastoIn) -> GastoOut:
    gasto = repo.gasto_de(db, usuario.id, gasto_id)
    if gasto is None:
        raise NotFoundError("No encontré ese gasto.")
    _validar_vinculos(db, usuario.id, datos)
    _revertir(db, usuario.id, gasto)
    db.flush()
    dia = _fecha(datos.fecha)
    foto = _foto_del_gasto(db, usuario, dia, excluir=gasto.id)
    visto = proyectar(foto, datos.monto, datos.categoria)
    origen, explicacion = _explicacion(datos, visto.nivel)
    gasto.monto = datos.monto
    gasto.descripcion = datos.descripcion.strip()
    gasto.categoria = datos.categoria
    gasto.fecha = dia
    gasto.origen = origen
    gasto.nivel_alerta = _nivel(visto.nivel)
    gasto.explicacion = explicacion
    gasto.deuda_id = datos.deuda_id
    gasto.cuenta_fija_id = datos.cuenta_fija_id
    _aplicar(db, usuario, gasto, visto.cubierto_por_colchon, foto.ciclo.inicio)
    db.flush()
    return _salida(gasto, visto.frase)


def eliminar(db: Session, usuario: Usuario, gasto_id: str) -> None:
    gasto = repo.gasto_de(db, usuario.id, gasto_id)
    if gasto is None:
        raise NotFoundError("No encontré ese gasto.")
    _revertir(db, usuario.id, gasto)
    db.delete(gasto)
    db.flush()


def listar(db: Session, usuario: Usuario, todos: bool = False) -> list[GastoOut]:
    if todos:
        filas = repo.gastos_todos(db, usuario.id)
    else:
        foto = presupuesto.preparar(db, usuario)
        filas = repo.gastos_entre(db, usuario.id, foto.ciclo.inicio, foto.ciclo.fin)
    return [_salida(g) for g in filas]
