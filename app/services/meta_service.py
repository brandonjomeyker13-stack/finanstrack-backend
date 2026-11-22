from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.metas import MetaVista, proyectar_meta
from app.models import Meta, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import MetaIn, MetaOut, MetaPatch
from app.services import presupuesto_service as presupuesto


def _salida(meta: Meta, foto) -> MetaOut:
    proy = proyectar_meta(
        MetaVista(
            meta.nombre,
            meta.monto_objetivo,
            meta.monto_ahorrado,
            meta.aporte_por_ciclo,
            meta.fecha_deseada,
        ),
        foto,
    )
    progreso = 0.0 if meta.monto_objetivo <= 0 else meta.monto_ahorrado / meta.monto_objetivo
    return MetaOut(
        id=meta.id,
        nombre=meta.nombre,
        monto_objetivo=meta.monto_objetivo,
        monto_ahorrado=meta.monto_ahorrado,
        aporte_por_ciclo=meta.aporte_por_ciclo,
        fecha_deseada=meta.fecha_deseada,
        restante=proy.restante,
        ciclos_al_ritmo=proy.ciclos_al_ritmo,
        fecha_estimada=proy.fecha_estimada,
        aporte_posible_hoy=proy.aporte_posible_hoy,
        no_cabe_este_ciclo=proy.no_cabe_este_ciclo,
        llega_a_tiempo=proy.llega_a_tiempo,
        aporte_para_la_fecha=proy.aporte_para_la_fecha,
        frase=proy.frase,
        progreso=max(0.0, min(1.0, progreso)),
    )


def listar(db: Session, usuario: Usuario) -> list[MetaOut]:
    foto = presupuesto.preparar(db, usuario)
    return [_salida(m, foto) for m in repo.metas_de(db, usuario.id)]


def crear(db: Session, usuario: Usuario, datos: MetaIn) -> MetaOut:
    presupuesto.requerir_perfil(db, usuario.id)
    if datos.monto_ahorrado < 0 or datos.aporte_por_ciclo < 0:
        raise ValidationError("Esos montos no pueden ser negativos.")
    fila = Meta(
        usuario_id=usuario.id,
        nombre=datos.nombre.strip(),
        monto_objetivo=datos.monto_objetivo,
        monto_ahorrado=datos.monto_ahorrado,
        aporte_por_ciclo=datos.aporte_por_ciclo,
        fecha_deseada=datos.fecha_deseada,
    )
    db.add(fila)
    db.flush()
    foto = presupuesto.preparar(db, usuario)
    return _salida(fila, foto)


def actualizar(db: Session, usuario: Usuario, meta_id: str, datos: MetaPatch) -> MetaOut:
    meta = repo.meta_de(db, usuario.id, meta_id)
    if meta is None or meta.archivada:
        raise NotFoundError("No encontré esa meta.")
    if datos.nombre is not None:
        meta.nombre = datos.nombre.strip()
    if datos.monto_objetivo is not None:
        meta.monto_objetivo = datos.monto_objetivo
    if datos.monto_ahorrado is not None:
        meta.monto_ahorrado = datos.monto_ahorrado
    if datos.aporte_por_ciclo is not None:
        meta.aporte_por_ciclo = datos.aporte_por_ciclo
    if datos.quitar_fecha:
        meta.fecha_deseada = None
    elif datos.fecha_deseada is not None:
        meta.fecha_deseada = datos.fecha_deseada
    if not meta.nombre:
        raise ValidationError("Ponle un nombre a tu meta.")
    if meta.monto_objetivo <= 0:
        raise ValidationError("¿Cuánto necesitas para lograrla?")
    db.flush()
    foto = presupuesto.preparar(db, usuario)
    return _salida(meta, foto)


def archivar(db: Session, usuario: Usuario, meta_id: str) -> None:
    meta = repo.meta_de(db, usuario.id, meta_id)
    if meta is None:
        raise NotFoundError("No encontré esa meta.")
    meta.archivada = True
    db.flush()
