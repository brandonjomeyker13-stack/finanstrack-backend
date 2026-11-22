from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.finanzas import (
    AbonoIn,
    AporteIn,
    CuentaIn,
    CuentaOut,
    CuentaPatch,
    ColchonOut,
    DeudaIn,
    DeudaOut,
    DeudaPatch,
    GastoIn,
    GastoOut,
    ImpactoIn,
    ImpactoOut,
    IngresoIn,
    IngresoOut,
    IngresoPatch,
    MetaIn,
    MetaOut,
    MetaPatch,
    OnboardingIn,
    PagoCuentaIn,
    PerfilIn,
    PerfilOut,
    PresupuestoOut,
    InformeOut,
    SaldoIn,
)
from app.services import (
    colchon_service,
    cuenta_service,
    deuda_service,
    gasto_service,
    ingreso_service,
    informe_service,
    meta_service,
    perfil_service,
    presupuesto_service,
)

router = APIRouter(tags=["finanzas"])


def _db_usuario(
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    return db, usuario


@router.post("/onboarding", response_model=PerfilOut, status_code=status.HTTP_201_CREATED)
def onboarding(datos: OnboardingIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return perfil_service.empezar(db, usuario, datos)


@router.get("/perfil", response_model=PerfilOut)
def ver_perfil(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return perfil_service.ver(db, usuario)


@router.put("/perfil", response_model=PerfilOut)
def actualizar_perfil(datos: PerfilIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return perfil_service.actualizar(db, usuario, datos)


@router.get("/presupuesto", response_model=PresupuestoOut)
def presupuesto(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return presupuesto_service.ver(db, usuario)


@router.get("/informe", response_model=InformeOut)
def informe(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return informe_service.ver(db, usuario)


@router.post("/presupuesto/impacto", response_model=ImpactoOut)
def impacto(datos: ImpactoIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return presupuesto_service.impacto(db, usuario, datos)


@router.post("/presupuesto/saldo", response_model=PresupuestoOut)
def declarar_saldo(datos: SaldoIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return presupuesto_service.declarar_saldo(db, usuario, datos)


@router.get("/ingresos", response_model=list[IngresoOut])
def ingresos(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return ingreso_service.listar(db, usuario)


@router.post("/ingresos", response_model=IngresoOut, status_code=status.HTTP_201_CREATED)
def crear_ingreso(datos: IngresoIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return ingreso_service.crear(db, usuario, datos)


class _ConfirmarIn(BaseModel):
    monto: int | None = Field(default=None, gt=0, le=999_999_999_999)


@router.post("/ingresos/{ingreso_id}/confirmar", response_model=IngresoOut)
def confirmar_ingreso(ingreso_id: str, datos: _ConfirmarIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return ingreso_service.confirmar(db, usuario, ingreso_id, datos.monto)


@router.patch("/ingresos/{ingreso_id}", response_model=IngresoOut)
def editar_ingreso(ingreso_id: str, datos: IngresoPatch, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return ingreso_service.actualizar(db, usuario, ingreso_id, datos)


@router.delete("/ingresos/{ingreso_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_ingreso(ingreso_id: str, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    ingreso_service.eliminar(db, usuario, ingreso_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/gastos", response_model=list[GastoOut])
def gastos(todos: bool = False, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return gasto_service.listar(db, usuario, todos=todos)


@router.post("/gastos", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def crear_gasto(datos: GastoIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return gasto_service.registrar(db, usuario, datos)


@router.put("/gastos/{gasto_id}", response_model=GastoOut)
def editar_gasto(gasto_id: str, datos: GastoIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return gasto_service.corregir(db, usuario, gasto_id, datos)


@router.delete("/gastos/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_gasto(gasto_id: str, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    gasto_service.eliminar(db, usuario, gasto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/deudas", response_model=list[DeudaOut])
def deudas(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return deuda_service.listar(db, usuario)


@router.post("/deudas", response_model=DeudaOut, status_code=status.HTTP_201_CREATED)
def crear_deuda(datos: DeudaIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return deuda_service.crear(db, usuario, datos)


@router.patch("/deudas/{deuda_id}", response_model=DeudaOut)
def editar_deuda(deuda_id: str, datos: DeudaPatch, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return deuda_service.actualizar(db, usuario, deuda_id, datos)


@router.delete("/deudas/{deuda_id}", status_code=status.HTTP_204_NO_CONTENT)
def archivar_deuda(deuda_id: str, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    deuda_service.archivar(db, usuario, deuda_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/deudas/{deuda_id}/abonar", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def abonar_deuda(deuda_id: str, datos: AbonoIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return deuda_service.abonar(db, usuario, deuda_id, datos)


@router.get("/cuentas-fijas", response_model=list[CuentaOut])
def cuentas(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return cuenta_service.listar(db, usuario)


@router.post("/cuentas-fijas", response_model=CuentaOut, status_code=status.HTTP_201_CREATED)
def crear_cuenta(datos: CuentaIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return cuenta_service.crear(db, usuario, datos)


@router.patch("/cuentas-fijas/{cuenta_id}", response_model=CuentaOut)
def editar_cuenta(cuenta_id: str, datos: CuentaPatch, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return cuenta_service.actualizar(db, usuario, cuenta_id, datos)


@router.delete("/cuentas-fijas/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
def archivar_cuenta(cuenta_id: str, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    cuenta_service.archivar(db, usuario, cuenta_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cuentas-fijas/{cuenta_id}/pagar", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def pagar_cuenta(cuenta_id: str, datos: PagoCuentaIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return cuenta_service.pagar(db, usuario, cuenta_id, datos)


@router.get("/colchon", response_model=ColchonOut)
def colchon(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return colchon_service.ver(db, usuario)


@router.post("/colchon/aportar", response_model=ColchonOut, status_code=status.HTTP_201_CREATED)
def aportar_colchon(datos: AporteIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return colchon_service.aportar(db, usuario, datos)


@router.get("/metas", response_model=list[MetaOut])
def metas(ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return meta_service.listar(db, usuario)


@router.post("/metas", response_model=MetaOut, status_code=status.HTTP_201_CREATED)
def crear_meta(datos: MetaIn, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return meta_service.crear(db, usuario, datos)


@router.patch("/metas/{meta_id}", response_model=MetaOut)
def editar_meta(meta_id: str, datos: MetaPatch, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    return meta_service.actualizar(db, usuario, meta_id, datos)


@router.delete("/metas/{meta_id}", status_code=status.HTTP_204_NO_CONTENT)
def archivar_meta(meta_id: str, ctx=Depends(_db_usuario)):
    db, usuario = ctx
    meta_service.archivar(db, usuario, meta_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
