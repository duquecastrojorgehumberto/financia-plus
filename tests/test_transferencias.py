"""Pruebas de transferencias con cargos (Tarea 11: RF-06, RF-07; RN-33 a RN-38, RN-72).

Qué verifican
    * CA-02: transferir 200.000 de Nequi a Nubank con un cargo de 800.
    * CA-03: si un cargo falla, no queda ni la transferencia ni ningún cargo.
    * CA-04: anular la transferencia devuelve los saldos y anula sus cargos.
    * Corregir la transferencia y sus cargos (RN-72, RN-35), agregar un cargo,
      reactivar, cuentas archivadas (RN-12) y datos de otro usuario (RN-06).
    * La API /api/transferencias.

Usan con_tx, cliente_api y Mundo (conftest.py): no dejan datos en la base.
Mundo trae Nequi (saldo inicial 100.000) y Nubank (0).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.movimientos import MovimientoRepositorio
from app.servicios.categorias import CategoriaServicio
from app.servicios.cuentas import CuentaServicio
from app.servicios.movimientos import FiltroHistorial, MovimientoServicio
from app.servicios.transferencias import DatosCargo, DatosTransferencia, TransferenciaServicio
from conftest import FECHA, Mundo

ENCABEZADOS = {"X-Requested-With": "financia"}


@pytest.fixture
def m(con_tx):
    mundo = Mundo(con_tx)
    impuestos = next(r for r in CategoriaServicio(con_tx).listar_arbol(mundo.u, "EGRESO")
                     if r.raiz.nombre == "Impuestos y comisiones")
    mundo.cuatro_por_mil = next(s.id_categoria for s in impuestos.subcategorias if s.nombre == "4×1.000")
    return mundo


@pytest.fixture
def servicio(con_tx):
    return TransferenciaServicio(con_tx)


def datos(m, monto="200000", *, origen=None, destino=None, fecha=FECHA, cargos=(), descripcion=None):
    return DatosTransferencia(id_cuenta_origen=origen or m.nequi, id_cuenta_destino=destino or m.nubank,
                              monto=Decimal(monto), fecha=fecha, descripcion=descripcion, cargos=list(cargos))


def cargo(categoria, monto="800", descripcion=None):
    return DatosCargo(monto=Decimal(monto), id_categoria=categoria, descripcion=descripcion)


def total(con, id_usuario, tipo) -> Decimal:
    """Ingresos o egresos VIGENTES de noviembre de 2026 (RN-64), como los sumará el resumen."""
    return con.execute(
        "SELECT COALESCE(SUM(monto), 0) AS total FROM movimiento WHERE id_usuario = %s AND tipo = %s "
        "AND estado = 'VIGENTE' AND fecha BETWEEN '2026-11-01' AND '2026-11-30'",
        (id_usuario, tipo),
    ).fetchone()["total"]


def filas(con, id_usuario) -> int:
    return con.execute("SELECT count(*) AS n FROM movimiento WHERE id_usuario = %s", (id_usuario,)).fetchone()["n"]


# =====================================================================
# 1. Registrar (RN-33 a RN-37)
# =====================================================================

def test_ca02_transferencia_con_cargo(servicio, con_tx, m):
    """CA-02: Nequi −200.800; Nubank +200.000; egresos +800; ingresos sin cambio."""
    servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil, "800")]))
    assert m.saldo(m.nequi) == Decimal("100000") - Decimal("200800")
    assert m.saldo(m.nubank) == Decimal("200000.00")
    assert total(con_tx, m.u, "EGRESO") == Decimal("800.00")
    assert total(con_tx, m.u, "INGRESO") == Decimal("0")


def test_la_transferencia_es_una_fila_y_el_cargo_otra(servicio, m):
    """RN-33, RN-34, RN-35: el cargo es un EGRESO de la cuenta de origen, con la misma fecha."""
    t = servicio.registrar(m.u, datos(m, fecha=date(2026, 11, 7), cargos=[cargo(m.cuatro_por_mil)]))
    transferencia = t.transferencia.movimiento
    assert (transferencia.tipo, transferencia.id_cuenta, transferencia.id_cuenta_destino,
            transferencia.id_categoria) == ("TRANSFERENCIA", m.nequi, m.nubank, None)
    [c] = t.cargos
    assert (c.movimiento.tipo, c.movimiento.id_cuenta, c.movimiento.fecha, c.movimiento.id_transferencia) == (
        "EGRESO", m.nequi, date(2026, 11, 7), transferencia.id_movimiento)
    assert c.nombre_categoria == "4×1.000"


def test_varios_cargos(servicio, m):
    """RN-34: cero o más cargos; total_cargos suma los vigentes."""
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil, "800"),
                                                 cargo(m.impuestos, "7500", "Comisión ACH")]))
    assert [c.movimiento.monto for c in t.cargos] == [Decimal("800.00"), Decimal("7500.00")]
    assert t.datos_publicos()["total_cargos"] == "8300.00"
    assert m.saldo(m.nequi) == Decimal("100000") - Decimal("208300")


def test_sin_cargos(servicio, con_tx, m):
    t = servicio.registrar(m.u, datos(m, "50000", descripcion="  Ahorro  "))
    assert t.cargos == []
    assert t.transferencia.movimiento.descripcion == "Ahorro"
    assert total(con_tx, m.u, "EGRESO") == Decimal("0")   # RN-33: no es gasto


def test_ca03_cargo_con_categoria_invalida_no_deja_nada(servicio, con_tx, m):
    """CA-03, RN-37: el segundo cargo tiene una categoría de INGRESO → no queda nada.

    La transferencia y el primer cargo SÍ alcanzaron a insertarse antes del
    error: es la transacción la que los deshace.
    """
    antes = filas(con_tx, m.u)
    with pytest.raises(ErrorNegocio, match="es de tipo INGRESO"):
        servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil), cargo(m.salario)]))
    assert filas(con_tx, m.u) == antes
    assert m.saldo(m.nequi) == Decimal("100000.00")


def test_ca03_falla_tecnica_al_guardar_un_cargo(servicio, con_tx, m, monkeypatch):
    """CA-03, RN-37: aunque el error sea inesperado (no una regla), no queda nada."""
    original = MovimientoRepositorio.insertar_cargo
    llamadas = {"n": 0}

    def insertar_que_falla(self, *args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise RuntimeError("falla simulada en el segundo cargo")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MovimientoRepositorio, "insertar_cargo", insertar_que_falla)
    antes = filas(con_tx, m.u)
    with pytest.raises(RuntimeError):
        servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil), cargo(m.impuestos)]))
    assert filas(con_tx, m.u) == antes


def test_cargo_con_categoria_de_otro_usuario_no_deja_nada(servicio, con_tx, m):
    """CA-03, CA-06."""
    otro = Mundo(con_tx)
    antes = filas(con_tx, m.u)
    with pytest.raises(NoEncontrado, match="categoría"):
        servicio.registrar(m.u, datos(m, cargos=[cargo(otro.impuestos)]))
    assert filas(con_tx, m.u) == antes


@pytest.mark.parametrize("armar, mensaje", [
    (lambda m: datos(m, destino=m.nequi), "deben ser distintas"),
    (lambda m: datos(m, "0"), "monto de la transferencia debe ser mayor que cero"),
    (lambda m: datos(m, "10.001"), "máximo 2 decimales"),
    (lambda m: datos(m, cargos=[cargo(m.cuatro_por_mil, "0")]), "monto del cargo debe ser mayor que cero"),
])
def test_datos_invalidos(servicio, m, armar, mensaje):
    """RN-33 (origen distinto de destino) y RN-30 (montos mayores que cero)."""
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.registrar(m.u, armar(m))


def test_cuenta_archivada(servicio, con_tx, m):
    """RN-12: ni origen ni destino pueden estar archivadas."""
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.registrar(m.u, datos(m))
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.registrar(m.u, datos(m, origen=m.nubank, destino=m.nequi))


def test_cuenta_de_otro_usuario(servicio, con_tx, m):
    """CA-06, RN-06: transferir a una cuenta ajena es "no encontrado"."""
    otro = Mundo(con_tx)
    with pytest.raises(NoEncontrado, match="cuenta"):
        servicio.registrar(m.u, datos(m, destino=otro.nequi))
    assert m.saldo(m.nequi) == Decimal("100000.00")


def test_cargo_con_categoria_desactivada(servicio, con_tx, m):
    """RN-25."""
    CategoriaServicio(con_tx).desactivar(m.u, m.impuestos)
    with pytest.raises(ErrorNegocio, match="desactivada"):
        servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil)]))


# =====================================================================
# 2. Anular y reactivar (RN-38, RN-71, CA-04)
# =====================================================================

def test_ca04_anular_devuelve_los_saldos_y_anula_los_cargos(servicio, con_tx, m):
    """CA-04: saldos como antes; el cargo queda anulado."""
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil)]))
    anulada = servicio.anular(m.u, t.transferencia.movimiento.id_movimiento)
    assert anulada.transferencia.movimiento.estado == "ANULADO"
    assert [c.movimiento.estado for c in anulada.cargos] == ["ANULADO"]
    assert (m.saldo(m.nequi), m.saldo(m.nubank)) == (Decimal("100000.00"), Decimal("0.00"))
    assert total(con_tx, m.u, "EGRESO") == Decimal("0")
    # Siguen en el historial (RN-70).
    assert len(MovimientoServicio(con_tx).historial(m.u, FiltroHistorial(estado="ANULADO"))) == 2


def test_anular_dos_veces(servicio, m):
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    servicio.anular(m.u, id_t)
    with pytest.raises(ErrorNegocio, match="ya está anulada"):
        servicio.anular(m.u, id_t)


def test_anular_con_una_cuenta_archivada(servicio, con_tx, m):
    """RN-12: si una de las dos cuentas está archivada, no se anula."""
    id_t = servicio.registrar(m.u, datos(m, "1000")).transferencia.movimiento.id_movimiento
    MovimientoServicio(con_tx).registrar(m.u, "EGRESO", m.datos("1000", cuenta=m.nubank))   # Nubank queda en 0
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.anular(m.u, id_t)


def test_reactivar_solo_reactiva_la_transferencia(servicio, con_tx, m):
    """Los cargos se reactivan uno por uno: no se sabe cuáles se habían anulado a propósito."""
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil, "800"), cargo(m.impuestos, "500")]))
    id_t = t.transferencia.movimiento.id_movimiento
    id_cargo_1, id_cargo_2 = (c.movimiento.id_movimiento for c in t.cargos)
    MovimientoServicio(con_tx).anular(m.u, id_cargo_2)   # anulado a propósito, antes
    servicio.anular(m.u, id_t)

    reactivada = servicio.reactivar(m.u, id_t)
    assert reactivada.transferencia.movimiento.estado == "VIGENTE"
    assert [c.movimiento.estado for c in reactivada.cargos] == ["ANULADO", "ANULADO"]

    MovimientoServicio(con_tx).reactivar(m.u, id_cargo_1)
    assert m.saldo(m.nequi) == Decimal("100000") - Decimal("200800")


def test_reactivar_una_vigente(servicio, m):
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="ya está vigente"):
        servicio.reactivar(m.u, id_t)


# =====================================================================
# 3. Corregir (RN-72, RN-35) y agregar cargos
# =====================================================================

def test_corregir_monto_destino_fecha_y_descripcion(servicio, con_tx, m):
    efectivo = CuentaServicio(con_tx).crear(m.u, "Efectivo", "EFECTIVO", Decimal("0")).cuenta.id_cuenta
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil)]))
    corregida = servicio.corregir(m.u, t.transferencia.movimiento.id_movimiento,
                                  datos(m, "150000", destino=efectivo, fecha=date(2026, 11, 9), descripcion="Retiro"))
    mov = corregida.transferencia.movimiento
    assert (mov.monto, mov.id_cuenta_destino, mov.fecha, mov.descripcion) == (
        Decimal("150000.00"), efectivo, date(2026, 11, 9), "Retiro")
    # RN-35: el cargo sigue a la transferencia en la fecha; su monto no cambia.
    assert [(c.movimiento.fecha, c.movimiento.monto) for c in corregida.cargos] == [(date(2026, 11, 9), Decimal("800.00"))]
    assert m.saldo(m.nubank) == Decimal("0.00")
    assert m.saldo(efectivo) == Decimal("150000.00")


def test_no_se_cambia_el_origen_si_hay_cargos(servicio, con_tx, m):
    """RN-72: la FK del cargo lo impediría; el servicio lo explica antes."""
    efectivo = CuentaServicio(con_tx).crear(m.u, "Efectivo", "EFECTIVO", Decimal("0")).cuenta.id_cuenta
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil)]))
    with pytest.raises(ErrorNegocio, match="origen no se puede cambiar"):
        servicio.corregir(m.u, t.transferencia.movimiento.id_movimiento, datos(m, origen=efectivo))


def test_sin_cargos_si_se_cambia_el_origen(servicio, con_tx, m):
    efectivo = CuentaServicio(con_tx).crear(m.u, "Efectivo", "EFECTIVO", Decimal("0")).cuenta.id_cuenta
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    assert servicio.corregir(m.u, id_t, datos(m, origen=efectivo)).transferencia.movimiento.id_cuenta == efectivo
    assert m.saldo(m.nequi) == Decimal("100000.00")


def test_corregir_una_anulada(servicio, m):
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    servicio.anular(m.u, id_t)
    with pytest.raises(ErrorNegocio, match="Reactívela para corregirla"):
        servicio.corregir(m.u, id_t, datos(m, "1"))


def test_corregir_no_recibe_cargos(servicio, m):
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="uno por uno"):
        servicio.corregir(m.u, id_t, datos(m, cargos=[cargo(m.cuatro_por_mil)]))


def test_corregir_hacia_una_cuenta_archivada(servicio, con_tx, m):
    efectivo = CuentaServicio(con_tx).crear(m.u, "Efectivo", "EFECTIVO", Decimal("0")).cuenta.id_cuenta
    CuentaServicio(con_tx).archivar(m.u, efectivo)
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.corregir(m.u, id_t, datos(m, destino=efectivo))


def test_agregar_un_cargo_olvidado(servicio, m):
    id_t = servicio.registrar(m.u, datos(m, fecha=date(2026, 11, 3))).transferencia.movimiento.id_movimiento
    t = servicio.agregar_cargo(m.u, id_t, cargo(m.cuatro_por_mil, "800"))
    [c] = t.cargos
    assert (c.movimiento.id_cuenta, c.movimiento.fecha) == (m.nequi, date(2026, 11, 3))
    assert m.saldo(m.nequi) == Decimal("100000") - Decimal("200800")


def test_agregar_cargo_a_una_anulada(servicio, m):
    id_t = servicio.registrar(m.u, datos(m)).transferencia.movimiento.id_movimiento
    servicio.anular(m.u, id_t)
    with pytest.raises(ErrorNegocio, match="Reactívela para agregarle cargos"):
        servicio.agregar_cargo(m.u, id_t, cargo(m.cuatro_por_mil))


def test_corregir_un_cargo(servicio, m):
    """RN-72: monto, categoría y descripción; la cuenta y la fecha siguen siendo las de la transferencia."""
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil, "800")]))
    id_t, id_c = t.transferencia.movimiento.id_movimiento, t.cargos[0].movimiento.id_movimiento
    corregida = servicio.corregir_cargo(m.u, id_t, id_c, cargo(m.impuestos, "850", "Ajuste del banco"))
    c = corregida.cargos[0]
    assert (c.movimiento.monto, c.movimiento.id_categoria, c.movimiento.descripcion) == (
        Decimal("850.00"), m.impuestos, "Ajuste del banco")
    assert (c.movimiento.id_cuenta, c.movimiento.fecha) == (m.nequi, FECHA)


def test_corregir_cargo_con_categoria_de_ingreso(servicio, m):
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil)]))
    with pytest.raises(ErrorNegocio, match="es de tipo INGRESO"):
        servicio.corregir_cargo(m.u, t.transferencia.movimiento.id_movimiento,
                                t.cargos[0].movimiento.id_movimiento, cargo(m.salario))


def test_corregir_un_cargo_de_otra_transferencia(servicio, m):
    a = servicio.registrar(m.u, datos(m, "100", cargos=[cargo(m.cuatro_por_mil)]))
    b = servicio.registrar(m.u, datos(m, "200"))
    with pytest.raises(NoEncontrado, match="cargo"):
        servicio.corregir_cargo(m.u, b.transferencia.movimiento.id_movimiento,
                                a.cargos[0].movimiento.id_movimiento, cargo(m.impuestos))


def test_corregir_un_cargo_anulado(servicio, con_tx, m):
    t = servicio.registrar(m.u, datos(m, cargos=[cargo(m.cuatro_por_mil)]))
    id_c = t.cargos[0].movimiento.id_movimiento
    MovimientoServicio(con_tx).anular(m.u, id_c)
    with pytest.raises(ErrorNegocio, match="Reactívelo para corregirlo"):
        servicio.corregir_cargo(m.u, t.transferencia.movimiento.id_movimiento, id_c, cargo(m.impuestos))


# =====================================================================
# 4. Otro usuario y otros tipos (RN-06)
# =====================================================================

@pytest.mark.parametrize("accion", ["obtener", "anular", "reactivar", "corregir", "agregar_cargo"])
def test_transferencia_ajena(servicio, con_tx, m, accion):
    otro = Mundo(con_tx)
    ajena = servicio.registrar(otro.u, datos(otro)).transferencia.movimiento.id_movimiento
    argumentos = {"corregir": (datos(m),), "agregar_cargo": (cargo(m.impuestos),)}.get(accion, ())
    with pytest.raises(NoEncontrado, match="transferencia"):
        getattr(servicio, accion)(m.u, ajena, *argumentos)


def test_un_egreso_no_es_una_transferencia(servicio, con_tx, m):
    egreso = MovimientoServicio(con_tx).registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    with pytest.raises(NoEncontrado, match="transferencia"):
        servicio.obtener(m.u, egreso)
    with pytest.raises(NoEncontrado, match="transferencia"):
        servicio.anular(m.u, egreso)


# =====================================================================
# 5. API /api/transferencias
# =====================================================================

@pytest.fixture
def api(cliente_api):
    correo = f"api.{uuid.uuid4().hex[:10]}@prueba.example"
    cliente_api.post("/api/registro", headers=ENCABEZADOS,
                     json={"nombre": "Ana", "correo": correo, "clave": "clave-segura-123"})
    crear = lambda nombre, saldo: cliente_api.post("/api/cuentas", headers=ENCABEZADOS, json={   # noqa: E731
        "nombre": nombre, "tipo": "OTRA", "saldo_inicial": saldo}).get_json()["cuenta"]["id_cuenta"]
    impuestos = next(c for c in cliente_api.get("/api/categorias?tipo=EGRESO").get_json()["categorias"]
                     if c["nombre"] == "Impuestos y comisiones")
    return cliente_api, {"nequi": crear("Nequi", "500000"), "nubank": crear("Nubank", "0"),
                         "cuatro_por_mil": impuestos["subcategorias"][0]["id_categoria"],
                         "impuestos": impuestos["id_categoria"]}


def saldo_api(cliente, id_cuenta):
    return cliente.get(f"/api/cuentas/{id_cuenta}").get_json()["cuenta"]["saldo"]


def test_api_flujo_completo(api):
    cliente, d = api
    r = cliente.post("/api/transferencias", headers=ENCABEZADOS, json={
        "id_cuenta_origen": d["nequi"], "id_cuenta_destino": d["nubank"], "monto": "200000",
        "fecha": "2026-11-01", "cargos": [{"monto": "800", "id_categoria": d["cuatro_por_mil"]}]})
    assert r.status_code == 201
    t = r.get_json()["transferencia"]
    assert (t["tipo"], t["total_cargos"], len(t["cargos"])) == ("TRANSFERENCIA", "800.00", 1)
    assert (t["nombre_cuenta"], t["nombre_cuenta_destino"]) == ("Nequi", "Nubank")
    assert (saldo_api(cliente, d["nequi"]), saldo_api(cliente, d["nubank"])) == ("299200.00", "200000.00")

    assert cliente.get(f"/api/transferencias/{t['id_movimiento']}").get_json()["transferencia"]["cargos"][0]["monto"] == "800.00"
    historial = cliente.get("/api/movimientos?tipo=TRANSFERENCIA").get_json()["movimientos"]
    assert [x["id_movimiento"] for x in historial] == [t["id_movimiento"]]

    r = cliente.post(f"/api/transferencias/{t['id_movimiento']}/cargos", headers=ENCABEZADOS,
                     json={"monto": "3000", "id_categoria": d["impuestos"], "descripcion": "Comisión"})
    assert r.status_code == 201
    id_cargo = r.get_json()["transferencia"]["cargos"][1]["id_movimiento"]

    r = cliente.put(f"/api/transferencias/{t['id_movimiento']}/cargos/{id_cargo}", headers=ENCABEZADOS,
                    json={"monto": "2500", "id_categoria": d["impuestos"]})
    assert r.get_json()["transferencia"]["total_cargos"] == "3300.00"

    r = cliente.put(f"/api/transferencias/{t['id_movimiento']}", headers=ENCABEZADOS, json={
        "id_cuenta_origen": d["nequi"], "id_cuenta_destino": d["nubank"], "monto": "100000", "fecha": "2026-11-02"})
    assert r.get_json()["transferencia"]["cargos"][0]["fecha"] == "2026-11-02"

    r = cliente.post(f"/api/transferencias/{t['id_movimiento']}/anular", headers=ENCABEZADOS, json={})
    assert [c["estado"] for c in r.get_json()["transferencia"]["cargos"]] == ["ANULADO", "ANULADO"]
    assert (saldo_api(cliente, d["nequi"]), saldo_api(cliente, d["nubank"])) == ("500000.00", "0.00")

    r = cliente.post(f"/api/transferencias/{t['id_movimiento']}/reactivar", headers=ENCABEZADOS, json={})
    assert r.get_json()["transferencia"]["estado"] == "VIGENTE"


def test_api_anular_transferencia_desde_movimientos_es_rechazado(api):
    """Desde /api/movimientos no se puede: dejaría sus cargos vigentes (RN-38)."""
    cliente, d = api
    t = cliente.post("/api/transferencias", headers=ENCABEZADOS, json={
        "id_cuenta_origen": d["nequi"], "id_cuenta_destino": d["nubank"], "monto": "1",
        "fecha": "2026-11-01"}).get_json()["transferencia"]
    r = cliente.post(f"/api/movimientos/{t['id_movimiento']}/anular", headers=ENCABEZADOS, json={})
    assert r.status_code == 400
    assert "junto con sus cargos" in r.get_json()["error"]


@pytest.mark.parametrize("cambio, mensaje", [
    ({"cargos": {"monto": "800"}}, "lista de objetos"),
    ({"cargos": [{"monto": 800, "id_categoria": 1}]}, "no es texto"),
    ({"cargos": [{"monto": "800"}]}, "Falta el campo 'id_categoria'"),
    ({"cargos": [{"monto": "800", "id_categoria": 1, "id_cuenta": 2}]}, "Campos no permitidos"),
    ({"id_categoria": 1}, "Campos no permitidos"),
    ({"id_cuenta_destino": None}, "Falta el campo 'id_cuenta_destino'"),
])
def test_api_datos_mal_formados(api, cambio, mensaje):
    cliente, d = api
    cuerpo = {"id_cuenta_origen": d["nequi"], "id_cuenta_destino": d["nubank"], "monto": "100",
              "fecha": "2026-11-01", **cambio}
    r = cliente.post("/api/transferencias", headers=ENCABEZADOS, json=cuerpo)
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


def test_api_ca03_no_deja_nada(api):
    cliente, d = api
    salario = next(c for c in cliente.get("/api/categorias?tipo=INGRESO").get_json()["categorias"]
                   if c["nombre"] == "Salario")["id_categoria"]
    r = cliente.post("/api/transferencias", headers=ENCABEZADOS, json={
        "id_cuenta_origen": d["nequi"], "id_cuenta_destino": d["nubank"], "monto": "200000", "fecha": "2026-11-01",
        "cargos": [{"monto": "800", "id_categoria": d["cuatro_por_mil"]}, {"monto": "1", "id_categoria": salario}]})
    assert r.status_code == 400
    assert cliente.get("/api/movimientos").get_json()["movimientos"] == []
    assert saldo_api(cliente, d["nequi"]) == "500000.00"


@pytest.mark.parametrize("metodo, ruta", [
    ("post", "/api/transferencias"),
    ("get", "/api/transferencias/1"),
    ("put", "/api/transferencias/1"),
    ("post", "/api/transferencias/1/anular"),
    ("post", "/api/transferencias/1/reactivar"),
    ("post", "/api/transferencias/1/cargos"),
    ("put", "/api/transferencias/1/cargos/2"),
])
def test_api_sin_sesion_responde_401(cliente_api, metodo, ruta):
    r = getattr(cliente_api, metodo)(ruta, headers=ENCABEZADOS, json={})
    assert r.status_code == 401
