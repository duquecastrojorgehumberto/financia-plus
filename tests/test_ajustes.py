"""Pruebas de ajustes de saldo (Tarea 12: RF-17; RN-50 a RN-55; CA-11).

Qué verifican
    * CA-11: saldo calculado 480.000, saldo real 473.500 → AJUSTE_DISMINUCION de
      6.500; saldo 473.500; los ingresos y egresos del periodo no cambian (RN-53).
    * Aumento, diferencia cero (no se registra nada), saldo real negativo.
    * Motivo obligatorio, cuenta archivada, cuenta de otro usuario.
    * Anular y reactivar un ajuste (RN-54); corregir su fecha y motivo.
    * RN-55 con una carrera real entre dos conexiones: si otra transacción está
      registrando un movimiento en la cuenta, el ajuste espera y lo incluye.
    * La API.

Usan con_tx, cliente_api y Mundo (conftest.py). Mundo trae Nequi (100.000) y Nubank (0).
"""

import threading
import uuid
from datetime import date
from decimal import Decimal

import psycopg
import pytest

from app.errores import ErrorNegocio, NoEncontrado
from app.servicios.ajustes import AjusteServicio
from app.servicios.cuentas import CuentaServicio
from app.servicios.movimientos import FiltroHistorial, MovimientoServicio
from conftest import FECHA, Mundo, url_app_en_base_de_pruebas

ENCABEZADOS = {"X-Requested-With": "financia"}


@pytest.fixture
def m(con_tx):
    return Mundo(con_tx)


@pytest.fixture
def servicio(con_tx):
    return AjusteServicio(con_tx)


def total(con, id_usuario, tipo) -> Decimal:
    """Ingresos o egresos VIGENTES (RN-64), como los sumará el resumen."""
    return con.execute(
        "SELECT COALESCE(SUM(monto), 0) AS total FROM movimiento "
        "WHERE id_usuario = %s AND tipo = %s AND estado = 'VIGENTE'",
        (id_usuario, tipo),
    ).fetchone()["total"]


# =====================================================================
# 1. Ajustar (RN-50 a RN-53)
# =====================================================================

def test_ca11_ajuste_de_disminucion(servicio, con_tx, m):
    """CA-11."""
    MovimientoServicio(con_tx).registrar(m.u, "INGRESO", m.datos("380000", categoria=m.salario))
    assert m.saldo() == Decimal("480000.00")
    ingresos, egresos = total(con_tx, m.u, "INGRESO"), total(con_tx, m.u, "EGRESO")

    r = servicio.ajustar(m.u, m.nequi, Decimal("473500"), "Compras no registradas", FECHA)

    assert r.saldo_anterior == Decimal("480000.00")
    assert (r.ajuste.movimiento.tipo, r.ajuste.movimiento.monto) == ("AJUSTE_DISMINUCION", Decimal("6500.00"))
    assert r.ajuste.movimiento.descripcion == "Compras no registradas"
    assert r.ajuste.movimiento.id_categoria is None   # RN-52
    assert r.cuenta.saldo == Decimal("473500.00")
    assert m.saldo() == Decimal("473500.00")
    # RN-53: no es ingreso ni gasto.
    assert (total(con_tx, m.u, "INGRESO"), total(con_tx, m.u, "EGRESO")) == (ingresos, egresos)


def test_ajuste_de_aumento(servicio, m):
    """RN-51: diferencia positiva → AJUSTE_AUMENTO, monto positivo."""
    r = servicio.ajustar(m.u, m.nequi, Decimal("100250.50"), "Intereses no registrados")
    assert (r.ajuste.movimiento.tipo, r.ajuste.movimiento.monto) == ("AJUSTE_AUMENTO", Decimal("250.50"))
    assert m.saldo() == Decimal("100250.50")


def test_sin_diferencia_no_se_registra_nada(servicio, con_tx, m):
    """RN-51: diferencia cero → no se crea ningún movimiento."""
    r = servicio.ajustar(m.u, m.nequi, Decimal("100000.00"), "Revisión mensual")
    assert r.ajuste is None
    assert r.datos_publicos()["ajuste"] is None
    assert MovimientoServicio(con_tx).historial(m.u, FiltroHistorial()) == []


def test_saldo_real_negativo(servicio, m):
    """RN-14: una cuenta puede quedar en negativo; el ajuste lo refleja."""
    r = servicio.ajustar(m.u, m.nequi, Decimal("-500"), "Sobregiro")
    assert (r.ajuste.movimiento.tipo, r.ajuste.movimiento.monto) == ("AJUSTE_DISMINUCION", Decimal("100500.00"))
    assert r.cuenta.saldo_negativo()


def test_fecha_por_defecto_es_hoy(servicio, m):
    assert servicio.ajustar(m.u, m.nequi, Decimal("1"), "Prueba").ajuste.movimiento.fecha == date.today()


@pytest.mark.parametrize("saldo, motivo, mensaje", [
    ("100", "   ", "motivo del ajuste es obligatorio"),
    ("100.001", "Motivo", "máximo 2 decimales"),
    ("-1000000000000", "Motivo", "demasiado grande"),
])
def test_datos_invalidos(servicio, con_tx, m, saldo, motivo, mensaje):
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.ajustar(m.u, m.nequi, Decimal(saldo), motivo)
    assert MovimientoServicio(con_tx).historial(m.u, FiltroHistorial()) == []


def test_cuenta_archivada(servicio, con_tx, m):
    """RN-12."""
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.ajustar(m.u, m.nubank, Decimal("10"), "Motivo")


def test_cuenta_de_otro_usuario(servicio, con_tx, m):
    """RN-06."""
    otro = Mundo(con_tx)
    with pytest.raises(NoEncontrado, match="cuenta"):
        servicio.ajustar(m.u, otro.nequi, Decimal("0"), "Intento")
    assert otro.saldo() == Decimal("100000.00")


# =====================================================================
# 2. Anular, reactivar y corregir (RN-54)
# =====================================================================

def test_anular_y_reactivar_un_ajuste(servicio, con_tx, m):
    """RN-54: el ajuste está en el historial y se anula como cualquier movimiento."""
    id_ajuste = servicio.ajustar(m.u, m.nequi, Decimal("90000"), "Cuadre").ajuste.movimiento.id_movimiento
    movimientos = MovimientoServicio(con_tx)
    assert [d.movimiento.id_movimiento for d in movimientos.historial(m.u, FiltroHistorial(tipo="AJUSTE_DISMINUCION"))] == [id_ajuste]
    movimientos.anular(m.u, id_ajuste)
    assert m.saldo() == Decimal("100000.00")
    movimientos.reactivar(m.u, id_ajuste)
    assert m.saldo() == Decimal("90000.00")


def test_corregir_fecha_y_motivo(servicio, m):
    r = servicio.ajustar(m.u, m.nequi, Decimal("90000"), "Cuadre", FECHA)
    corregido = servicio.corregir(m.u, r.ajuste.movimiento.id_movimiento, date(2026, 11, 15), "  Cuadre con extracto  ")
    c = corregido.movimiento
    assert (c.fecha, c.descripcion, c.monto) == (date(2026, 11, 15), "Cuadre con extracto", Decimal("10000.00"))


def test_corregir_sin_motivo(servicio, m):
    id_ajuste = servicio.ajustar(m.u, m.nequi, Decimal("1"), "Cuadre").ajuste.movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="motivo del ajuste es obligatorio"):
        servicio.corregir(m.u, id_ajuste, FECHA, "")


def test_corregir_un_ajuste_anulado(servicio, con_tx, m):
    id_ajuste = servicio.ajustar(m.u, m.nequi, Decimal("1"), "Cuadre").ajuste.movimiento.id_movimiento
    MovimientoServicio(con_tx).anular(m.u, id_ajuste)
    with pytest.raises(ErrorNegocio, match="Reactívelo para corregirlo"):
        servicio.corregir(m.u, id_ajuste, FECHA, "Otro motivo")


def test_corregir_con_la_cuenta_archivada(servicio, con_tx, m):
    id_ajuste = servicio.ajustar(m.u, m.nubank, Decimal("100"), "Cuadre").ajuste.movimiento.id_movimiento
    servicio.ajustar(m.u, m.nubank, Decimal("0"), "Vuelve a 0")
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.corregir(m.u, id_ajuste, FECHA, "Otro motivo")


def test_corregir_algo_que_no_es_un_ajuste(servicio, con_tx, m):
    egreso = MovimientoServicio(con_tx).registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    with pytest.raises(NoEncontrado, match="ajuste"):
        servicio.corregir(m.u, egreso, FECHA, "Motivo")


def test_corregir_ajuste_de_otro_usuario(servicio, con_tx, m):
    otro = Mundo(con_tx)
    ajeno = servicio.ajustar(otro.u, otro.nequi, Decimal("1"), "Cuadre").ajuste.movimiento.id_movimiento
    with pytest.raises(NoEncontrado, match="ajuste"):
        servicio.corregir(m.u, ajeno, FECHA, "Intento")


def test_el_monto_de_un_ajuste_no_se_corrige_desde_movimientos(con_tx, m, servicio):
    """Corregir un ajuste en /api/movimientos sigue rechazado (Tarea 10)."""
    id_ajuste = servicio.ajustar(m.u, m.nequi, Decimal("1"), "Cuadre").ajuste.movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="solo se corrigen ingresos y egresos"):
        MovimientoServicio(con_tx).corregir(m.u, id_ajuste, m.datos())


# =====================================================================
# 3. RN-55: carrera real entre dos conexiones
#
#     B (registra un ingreso)                A (ajuste: saldo real 5.000)
#     INSERT ingreso de 1.000 (sin COMMIT)
#                                            SELECT cuenta FOR UPDATE -> espera a B
#     COMMIT (medio segundo después)
#                                            calcula el saldo: 1.000 (ya incluye a B)
#                                            ajuste de AUMENTO por 4.000 -> saldo 5.000 ✔
#
# Sin el bloqueo, A calcularía con saldo 0, registraría un ajuste de 5.000, y
# al confirmar B el saldo quedaría en 6.000 en lugar del saldo real indicado.
# =====================================================================

def test_carrera_el_ajuste_espera_e_incluye_el_movimiento_en_curso(cuenta_confirmada, con_tx):
    u, cat, c = cuenta_confirmada
    with psycopg.connect(url_app_en_base_de_pruebas()) as b:
        b.execute("INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, monto, fecha) "
                  "VALUES (%s, 'INGRESO', %s, %s, 1000, %s)", (u, c, cat, FECHA))
        hilo = threading.Timer(0.5, b.commit)
        hilo.start()
        try:
            r = AjusteServicio(con_tx).ajustar(u, c, Decimal("5000"), "Cuadre", FECHA)
            assert r.saldo_anterior == Decimal("1000.00")
            assert (r.ajuste.movimiento.tipo, r.ajuste.movimiento.monto) == ("AJUSTE_AUMENTO", Decimal("4000.00"))
            assert r.cuenta.saldo == Decimal("5000.00")
        finally:
            hilo.join()
            con_tx.rollback()


# =====================================================================
# 4. API
# =====================================================================

@pytest.fixture
def api(cliente_api):
    correo = f"api.{uuid.uuid4().hex[:10]}@prueba.example"
    cliente_api.post("/api/registro", headers=ENCABEZADOS,
                     json={"nombre": "Ana", "correo": correo, "clave": "clave-segura-123"})
    nequi = cliente_api.post("/api/cuentas", headers=ENCABEZADOS, json={
        "nombre": "Nequi", "tipo": "OTRA", "saldo_inicial": "480000"}).get_json()["cuenta"]["id_cuenta"]
    return cliente_api, nequi


def test_api_ca11(api):
    cliente, nequi = api
    r = cliente.post(f"/api/cuentas/{nequi}/ajustes", headers=ENCABEZADOS,
                     json={"saldo_real": "473500", "motivo": "Compras no registradas", "fecha": "2026-11-20"})
    assert r.status_code == 201
    datos = r.get_json()
    assert datos["saldo_anterior"] == "480000.00"
    assert datos["cuenta"]["saldo"] == "473500.00"
    ajuste = datos["ajuste"]
    assert (ajuste["tipo"], ajuste["monto"], ajuste["descripcion"], ajuste["fecha"]) == (
        "AJUSTE_DISMINUCION", "6500.00", "Compras no registradas", "2026-11-20")

    r = cliente.put(f"/api/ajustes/{ajuste['id_movimiento']}", headers=ENCABEZADOS,
                    json={"fecha": "2026-11-21", "motivo": "Compras en efectivo"})
    assert r.status_code == 200
    assert r.get_json()["ajuste"]["descripcion"] == "Compras en efectivo"

    r = cliente.post(f"/api/movimientos/{ajuste['id_movimiento']}/anular", headers=ENCABEZADOS, json={})
    assert r.status_code == 200
    assert cliente.get(f"/api/cuentas/{nequi}").get_json()["cuenta"]["saldo"] == "480000.00"


def test_api_sin_diferencia_responde_200_sin_ajuste(api):
    cliente, nequi = api
    r = cliente.post(f"/api/cuentas/{nequi}/ajustes", headers=ENCABEZADOS,
                     json={"saldo_real": "480000.00", "motivo": "Revisión"})
    assert r.status_code == 200
    assert r.get_json()["ajuste"] is None


@pytest.mark.parametrize("cuerpo, mensaje", [
    ({"saldo_real": 473500, "motivo": "M"}, "no es texto"),
    ({"saldo_real": "473500"}, "Falta el campo 'motivo'"),
    ({"saldo_real": "1", "motivo": "M", "tipo": "AJUSTE_AUMENTO"}, "Campos no permitidos"),
    ({"saldo_real": "1", "motivo": "M", "fecha": "20/11/2026"}, "AAAA-MM-DD"),
])
def test_api_datos_mal_formados(api, cuerpo, mensaje):
    cliente, nequi = api
    r = cliente.post(f"/api/cuentas/{nequi}/ajustes", headers=ENCABEZADOS, json=cuerpo)
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


def test_api_corregir_no_acepta_monto(api):
    """El monto del ajuste no se corrige: se anula y se ajusta de nuevo."""
    cliente, nequi = api
    id_ajuste = cliente.post(f"/api/cuentas/{nequi}/ajustes", headers=ENCABEZADOS, json={
        "saldo_real": "1", "motivo": "M"}).get_json()["ajuste"]["id_movimiento"]
    r = cliente.put(f"/api/ajustes/{id_ajuste}", headers=ENCABEZADOS,
                    json={"fecha": "2026-11-21", "motivo": "M", "monto": "5"})
    assert r.status_code == 400
    assert "Campos no permitidos: monto" in r.get_json()["error"]


@pytest.mark.parametrize("metodo, ruta", [("post", "/api/cuentas/1/ajustes"), ("put", "/api/ajustes/1")])
def test_api_sin_sesion_responde_401(cliente_api, metodo, ruta):
    assert getattr(cliente_api, metodo)(ruta, headers=ENCABEZADOS, json={}).status_code == 401
