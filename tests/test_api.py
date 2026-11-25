import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def _base_limpia():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def cliente():
    with TestClient(app) as cliente:
        yield cliente


def _entrar(cliente: TestClient, email="ana@example.com"):
    respuesta = cliente.post(
        "/api/v1/auth/registro",
        json={"nombre": "Ana", "email": email, "password": "secreto123"},
    )
    assert respuesta.status_code == 201, respuesta.text
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _empezar(cliente, headers, situacion="ya_llego", **extra):
    cuerpo = {
        "frecuencia": "mensual",
        "dia_de_corte": 1,
        "monto_pago": 2_500_000,
        "nombre_pago": "Sueldo",
        "situacion": situacion,
    }
    cuerpo.update(extra)
    respuesta = cliente.post("/api/v1/onboarding", json=cuerpo, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta


def test_salud():
    with TestClient(app) as cliente:
        assert cliente.get("/health").json()["status"] == "ok"


def test_registro_y_el_pago_se_reparte(cliente):
    headers = _entrar(cliente)
    _empezar(cliente, headers)
    foto = cliente.get("/api/v1/presupuesto", headers=headers)
    assert foto.status_code == 200, foto.text
    cuerpo = foto.json()
    assert cuerpo["disponible_para_gastar"] == 2_250_000
    assert cuerpo["colchon"]["saldo"] == 250_000
    assert cuerpo["por_dia"] > 0
    assert cuerpo["estado"] == "en_orden"
    assert cuerpo["pago_fijo"]["confirmado"] is True


def test_un_pago_que_todavia_no_llega_no_se_gasta(cliente):
    headers = _entrar(cliente)
    _empezar(cliente, headers, situacion="lo_espero")
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["estado"] == "esperando_pago"
    assert foto["disponible_para_gastar"] == 0
    pago_id = foto["pago_fijo"]["id"]
    confirmado = cliente.post(
        f"/api/v1/ingresos/{pago_id}/confirmar",
        json={},
        headers=headers,
    )
    assert confirmado.status_code == 200, confirmado.text
    despues = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert despues["disponible_para_gastar"] == 2_250_000


def test_me_queda_no_inventa_el_sueldo(cliente):
    headers = _entrar(cliente)
    _empezar(cliente, headers, situacion="me_queda", me_queda=80_000)
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["estado"] == "con_lo_que_queda"
    assert foto["disponible_para_gastar"] == 80_000
    assert foto["pago_fijo"] is None


def test_un_gasto_baja_el_disponible_y_el_que_no_alcanza_pide_de_donde(cliente):
    headers = _entrar(cliente)
    _empezar(cliente, headers)
    ok = cliente.post(
        "/api/v1/gastos",
        json={"monto": 20_000, "descripcion": "Almuerzo", "categoria": "variable"},
        headers=headers,
    )
    assert ok.status_code == 201, ok.text
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["disponible_para_gastar"] == 2_230_000

    malo = cliente.post(
        "/api/v1/gastos",
        json={"monto": 9_000_000, "descripcion": "Moto", "categoria": "gustos"},
        headers=headers,
    )
    assert malo.status_code == 422
    assert malo.json()["codigo"] == "falta_explicacion"

    igual = cliente.post(
        "/api/v1/gastos",
        json={
            "monto": 9_000_000,
            "descripcion": "Moto",
            "categoria": "gustos",
            "explicacion": "Me prestó mi hermano",
            "origen": "prestamo",
        },
        headers=headers,
    )
    assert igual.status_code == 201, igual.text


def test_la_cuota_se_aparta_y_al_pagarla_baja_la_deuda(cliente):
    headers = _entrar(cliente)
    _empezar(cliente, headers)
    creada = cliente.post(
        "/api/v1/deudas",
        json={
            "nombre": "Tarjeta",
            "tipo": "cuotas",
            "monto_total": 900_000,
            "cuota_minima": 400_000,
            "dia_de_pago": 5,
            "tasa_interes_anual": 28,
        },
        headers=headers,
    )
    assert creada.status_code == 201, creada.text
    deuda = creada.json()
    assert deuda["compromiso"] == 400_000
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["reservas"]["cuotas"] == 400_000
    assert foto["disponible_para_gastar"] == 1_850_000

    pago = cliente.post(
        f"/api/v1/deudas/{deuda['id']}/abonar",
        json={"monto": 400_000, "como_cuota": True},
        headers=headers,
    )
    assert pago.status_code == 201, pago.text
    despues = cliente.get("/api/v1/deudas", headers=headers).json()[0]
    assert despues["saldo_pendiente"] == 500_000
    assert despues["cuota_pagada"] is True
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["reservas"]["cuotas"] == 0
    assert foto["disponible_para_gastar"] == 1_850_000


def test_borrar_un_abono_devuelve_el_saldo(cliente):
    headers = _entrar(cliente)
    _empezar(cliente, headers)
    deuda = cliente.post(
        "/api/v1/deudas",
        json={
            "nombre": "Celular",
            "tipo": "cuotas",
            "monto_total": 600_000,
            "cuota_minima": 100_000,
            "dia_de_pago": 10,
        },
        headers=headers,
    ).json()
    gasto = cliente.post(
        f"/api/v1/deudas/{deuda['id']}/abonar",
        json={"monto": 100_000, "como_cuota": True},
        headers=headers,
    ).json()
    borrado = cliente.delete(f"/api/v1/gastos/{gasto['id']}", headers=headers)
    assert borrado.status_code == 204
    saldo = cliente.get("/api/v1/deudas", headers=headers).json()[0]["saldo_pendiente"]
    assert saldo == 600_000


def test_correo_repetido(cliente):
    _entrar(cliente)
    otra = cliente.post(
        "/api/v1/auth/registro",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "secreto123"},
    )
    assert otra.status_code == 409


def _google(monkeypatch, payload):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cliente-de-prueba")

    def falso(token, client_id):
        assert token == "token-google-de-prueba-largo"
        assert client_id == "cliente-de-prueba"
        return payload

    monkeypatch.setattr("app.core.google_id.verificar_id_token", falso)


def test_google_sin_configurar(cliente, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    respuesta = cliente.post(
        "/api/v1/auth/google",
        json={"credential": "token-google-de-prueba-largo"},
    )
    assert respuesta.status_code == 422
    assert "GOOGLE_CLIENT_ID" in respuesta.json()["detail"]


def test_google_crea_la_cuenta_y_vuelve_a_entrar(cliente, monkeypatch):
    _google(
        monkeypatch,
        {
            "sub": "google-123",
            "email": "ana.google@gmail.com",
            "email_verified": True,
            "name": "Ana Google",
        },
    )
    creada = cliente.post(
        "/api/v1/auth/google",
        json={"credential": "token-google-de-prueba-largo"},
    )
    assert creada.status_code == 200, creada.text
    usuario = creada.json()["usuario"]
    assert usuario["email"] == "ana.google@gmail.com"
    assert usuario["nombre"] == "Ana Google"
    assert usuario["onboarding_completo"] is False

    otra = cliente.post(
        "/api/v1/auth/google",
        json={"credential": "token-google-de-prueba-largo"},
    )
    assert otra.status_code == 200
    assert otra.json()["usuario"]["id"] == usuario["id"]

    con_clave = cliente.post(
        "/api/v1/auth/login",
        json={"email": "ana.google@gmail.com", "password": "secreto123"},
    )
    assert con_clave.status_code == 401
    assert "Google" in con_clave.json()["detail"]


def test_google_enlaza_una_cuenta_que_ya_tenia_contrasena(cliente, monkeypatch):
    _entrar(cliente, email="ana@example.com")
    _google(
        monkeypatch,
        {
            "sub": "google-ana",
            "email": "ana@example.com",
            "email_verified": True,
            "name": "Otro nombre",
        },
    )
    con_google = cliente.post(
        "/api/v1/auth/google",
        json={"credential": "token-google-de-prueba-largo"},
    )
    assert con_google.status_code == 200, con_google.text
    assert con_google.json()["usuario"]["nombre"] == "Ana"
    con_clave = cliente.post(
        "/api/v1/auth/login",
        json={"email": "ana@example.com", "password": "secreto123"},
    )
    assert con_clave.status_code == 200


def test_informe_avisa_un_dia_antes_y_el_primer_periodo_no_se_compara(cliente, monkeypatch):
    from datetime import date

    dia = date(2026, 11, 22)
    monkeypatch.setattr("app.services.presupuesto_service.hoy_usuario", lambda: dia)
    monkeypatch.setattr("app.services.perfil_service.hoy_usuario", lambda: dia)
    headers = _entrar(cliente, email="rita@example.com")
    _empezar(cliente, headers)
    creada = cliente.post(
        "/api/v1/deudas",
        json={
            "nombre": "Celular",
            "tipo": "cuotas",
            "monto_total": 400_000,
            "cuota_minima": 100_000,
            "dia_de_pago": 23,
        },
        headers=headers,
    )
    assert creada.status_code == 201, creada.text
    informe = cliente.get("/api/v1/informe", headers=headers)
    assert informe.status_code == 200, informe.text
    cuerpo = informe.json()
    assert cuerpo["recordatorios"][0]["cuando"] == "manana"
    assert cuerpo["recordatorios"][0]["nombre"] == "Celular"
    assert cuerpo["anterior"] is None
    assert cuerpo["actual"]["ingresado"] == 2_500_000
    assert any("Mañana vence Celular" in frase for frase in cuerpo["consejos"])


def _guardar_reparto(cliente, headers, **cambios):
    cuerpo = {
        "frecuencia": "mensual",
        "dia_de_corte": 1,
        "segundo_dia_de_corte": None,
        "ancla_de_pago": None,
        "monto_pago": 2_500_000,
        "nombre_pago": "Sueldo",
        "pct_obligatorio": 45,
        "pct_deuda_extra": 15,
        "pct_variable": 20,
        "pct_gustos": 10,
        "pct_colchon": 10,
    }
    cuerpo.update(cambios)
    respuesta = cliente.put("/api/v1/perfil", json=cuerpo, headers=headers)
    assert respuesta.status_code == 200, respuesta.text


def test_cambiar_el_porcentaje_reemplaza_el_colchon_y_las_bolsas(cliente):
    headers = _entrar(cliente, email="reparto@example.com")
    _empezar(cliente, headers)
    antes = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert antes["colchon"]["saldo"] == 250_000
    cuentas = next(bolsa for bolsa in antes["bolsas"] if bolsa["id"] == "obligatorio")
    assert cuentas["asignado"] == 1_125_000

    _guardar_reparto(cliente, headers, pct_colchon=15, pct_gustos=5)
    subido = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert subido["colchon"]["aporte_del_ciclo"] == 375_000
    assert subido["colchon"]["saldo"] == 375_000
    gustos = next(bolsa for bolsa in subido["bolsas"] if bolsa["id"] == "gustos")
    assert gustos["asignado"] == 125_000
    repetido = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert repetido["colchon"]["saldo"] == 375_000

    _guardar_reparto(cliente, headers, pct_colchon=10, pct_gustos=10)
    bajado = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert bajado["colchon"]["aporte_del_ciclo"] == 250_000
    assert bajado["colchon"]["saldo"] == 250_000

    _guardar_reparto(cliente, headers, pct_obligatorio=50, pct_colchon=5)
    bolsas = cliente.get("/api/v1/presupuesto", headers=headers).json()
    cuentas = next(bolsa for bolsa in bolsas["bolsas"] if bolsa["id"] == "obligatorio")
    assert cuentas["asignado"] == 1_250_000
    assert cuentas["disponible"] == 1_250_000
    assert bolsas["colchon"]["saldo"] == 125_000


def test_meter_al_colchon_no_pasa_de_lo_que_queda(cliente):
    headers = _entrar(cliente, email="colchon@example.com")
    _empezar(cliente, headers, colchon_inicial=40_000)
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["disponible_para_gastar"] == 2_250_000
    assert foto["colchon"]["saldo"] == 290_000

    visto = cliente.get("/api/v1/colchon", headers=headers).json()
    assert visto["puedes_meter"] == 2_250_000
    de_mas = cliente.post("/api/v1/colchon/aportar", json={"monto": 2_250_001}, headers=headers)
    assert de_mas.status_code == 422

    metido = cliente.post("/api/v1/colchon/aportar", json={"monto": 100_000}, headers=headers)
    assert metido.status_code == 201, metido.text
    assert metido.json()["saldo"] == 390_000
    assert metido.json()["puedes_meter"] == 2_150_000

    despues = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert despues["disponible_para_gastar"] == 2_150_000
    gustos = next(bolsa for bolsa in despues["bolsas"] if bolsa["id"] == "gustos")
    assert gustos["disponible"] == 150_000
    otra = cliente.post("/api/v1/colchon/aportar", json={"monto": 2_150_001}, headers=headers)
    assert otra.status_code == 422


def test_abrir_el_periodo_dos_veces_no_duplica_el_colchon(cliente):
    headers = _entrar(cliente, email="carrera@example.com")
    _empezar(cliente, headers, situacion="lo_espero")
    foto = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert foto["colchon"]["saldo"] == 0
    confirmado = cliente.post(
        f"/api/v1/ingresos/{foto['pago_fijo']['id']}/confirmar",
        json={},
        headers=headers,
    )
    assert confirmado.status_code == 200, confirmado.text

    for ruta in ("/api/v1/presupuesto", "/api/v1/informe", "/api/v1/presupuesto"):
        respuesta = cliente.get(ruta, headers=headers)
        assert respuesta.status_code == 200, respuesta.text
    final = cliente.get("/api/v1/presupuesto", headers=headers).json()
    assert final["colchon"]["saldo"] == 250_000
    assert final["colchon"]["aporte_del_ciclo"] == 250_000


def test_borrar_la_cuenta_no_deja_entrar(cliente):
    headers = _entrar(cliente, email="borrar@example.com")
    _empezar(cliente, headers)
    rechazado = cliente.request(
        "DELETE",
        "/api/v1/auth/cuenta",
        json={"confirmacion": "no"},
        headers=headers,
    )
    assert rechazado.status_code == 422
    borrado = cliente.request(
        "DELETE",
        "/api/v1/auth/cuenta",
        json={"confirmacion": "BORRAR"},
        headers=headers,
    )
    assert borrado.status_code == 204, borrado.text
    assert cliente.get("/api/v1/auth/yo", headers=headers).status_code == 401
    assert (
        cliente.post(
            "/api/v1/auth/login",
            json={"email": "borrar@example.com", "password": "secreto123"},
        ).status_code
        == 401
    )
