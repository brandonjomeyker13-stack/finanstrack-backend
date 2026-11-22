from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationError
from app.core.fechas import hoy as hoy_usuario
from app.domain.ciclo import ciclo_que_contiene
from app.models import Ingreso, MovimientoFondo, Perfil, SaldoApertura, Usuario
from app.repositories import consultas as repo
from app.schemas.finanzas import OnboardingIn, PerfilIn, PerfilOut
from app.services import presupuesto_service as presupuesto
from app.services.reglas import reglas_de


def ver(db: Session, usuario: Usuario) -> PerfilOut:
    return presupuesto.perfil_vista(presupuesto.requerir_perfil(db, usuario.id))


def empezar(db: Session, usuario: Usuario, datos: OnboardingIn) -> PerfilOut:
    if repo.perfil_de(db, usuario.id) is not None:
        raise ConflictError("Ya empezaste. Los cambios van en Ajustes.")
    if datos.situacion == "me_queda" and datos.me_queda is None:
        raise ValidationError("Dime cuánto te queda hoy.")
    if datos.nombre and datos.nombre.strip():
        usuario.nombre = datos.nombre.strip()

    # Validar antes de guardar: un día de quincena imposible no deja fila a medias.
    perfil = Perfil(
        usuario_id=usuario.id,
        frecuencia=datos.frecuencia,
        dia_de_corte=datos.dia_de_corte,
        segundo_dia_de_corte=datos.segundo_dia_de_corte if datos.frecuencia == "quincenal" else None,
        ancla_de_pago=datos.ancla_de_pago if datos.frecuencia == "catorcenal" else None,
        monto_pago=datos.monto_pago,
        nombre_pago=datos.nombre_pago.strip(),
        pct_obligatorio=45,
        pct_deuda_extra=15,
        pct_variable=20,
        pct_gustos=10,
        pct_colchon=10,
    )
    reglas_de(perfil)
    db.add(perfil)
    db.flush()

    dia = hoy_usuario()
    ciclo = ciclo_que_contiene(dia, reglas_de(perfil))

    if datos.situacion == "ya_llego":
        db.add(
            Ingreso(
                usuario_id=usuario.id,
                monto=datos.monto_pago,
                fecha=ciclo.inicio,
                estado="confirmado",
                descripcion=perfil.nombre_pago,
                es_pago_fijo=True,
            )
        )
    elif datos.situacion == "me_queda":
        perfil.omitir_pago_ciclo = ciclo.inicio
        db.add(
            SaldoApertura(
                usuario_id=usuario.id,
                ciclo_inicio=ciclo.inicio,
                monto=datos.me_queda or 0,
                origen="declarado",
            )
        )

    if datos.colchon_inicial > 0:
        db.add(
            MovimientoFondo(
                usuario_id=usuario.id,
                tipo="aporte_manual",
                monto=datos.colchon_inicial,
                fecha=dia,
                ciclo_inicio=ciclo.inicio,
                motivo="Lo que ya tenías guardado al empezar",
            )
        )
    db.flush()
    presupuesto.preparar(db, usuario)
    return presupuesto.perfil_vista(perfil)


def actualizar(db: Session, usuario: Usuario, datos: PerfilIn) -> PerfilOut:
    perfil = presupuesto.requerir_perfil(db, usuario.id)
    perfil.frecuencia = datos.frecuencia
    perfil.dia_de_corte = datos.dia_de_corte
    perfil.segundo_dia_de_corte = datos.segundo_dia_de_corte if datos.frecuencia == "quincenal" else None
    perfil.ancla_de_pago = datos.ancla_de_pago if datos.frecuencia == "catorcenal" else None
    perfil.monto_pago = datos.monto_pago
    perfil.nombre_pago = datos.nombre_pago.strip()
    perfil.pct_obligatorio = datos.pct_obligatorio
    perfil.pct_deuda_extra = datos.pct_deuda_extra
    perfil.pct_variable = datos.pct_variable
    perfil.pct_gustos = datos.pct_gustos
    perfil.pct_colchon = datos.pct_colchon
    reglas_de(perfil)
    # El pago que todavía no llega se vuelve a armar con el ritmo nuevo.
    # El que ya confirmaste se queda: esa plata sí entró.
    repo.borrar_pagos_fijos_esperados(db, usuario.id)
    db.flush()
    presupuesto.preparar(db, usuario)
    return presupuesto.perfil_vista(perfil)

