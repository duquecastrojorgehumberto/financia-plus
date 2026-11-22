"""Pruebas del resumen financiero e indicadores (Tarea 14: RF-13, RF-15).

Qué verifican
    * Indicadores: RN-60 a RN-63 y CA-10 (disponible negativo con aviso; nada se bloquea).
    * Periodo: RN-64 (solo INGRESO y EGRESO vigentes del rango), RN-53 (ajustes aparte),
      RN-27 y CA-12 (subcategorías consolidadas en su raíz).
    * Los criterios de las tareas anteriores vistos desde el resumen:
      CA-01, CA-02 (los cargos son egresos; la transferencia no), CA-11 (el ajuste no
      cambia los egresos) y CA-14 (una categoría desactivada sigue sumando).
    * Porcentaje de cada categoría sobre el total de su tipo (para los gráficos).
    * Resumen mensual (últimos N meses, con 0 en los meses vacíos).
    * La API GET /api/resumen y GET /api/resumen/mensual.

Usan con_tx, cliente_api y Mundo (conftest.py). Mundo trae Nequi (100.000) y Nubank (0).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.errores import ErrorNegocio
from app.servicios.ajustes import AjusteServicio
from app.servicios.bolsillos import BolsilloServicio, DatosBolsillo
from app.servicios.categorias import CategoriaServicio
from app.servicios.cuentas import CuentaServicio
from app.servicios.movimientos import MovimientoServicio
from app.servicios.resumen import ResumenServicio, porcentaje
from app.servicios.transferencias import DatosCargo, DatosTransferencia, TransferenciaServicio
from conftest import FECHA, Mundo

ENCABEZADOS = {"X-Requested-With": "financia"}
NOVIEMBRE = (date(2026, 11, 1), date(2026, 11, 30))


@pytest.fixture
def m(con_tx):
    return Mundo(con_tx)


@pytest.fixture
def servicio(con_tx):
    return ResumenServicio(con_tx)


@pytest.fixture
def mov(con_tx):
    return MovimientoServicio(con_tx)


def noviembre(servicio, m):
    return servicio.periodo(m.u, *NOVIEMBRE)


def categoria(lista, nombre):
    return next(c for c in lista if c.nombre == nombre)


# =====================================================================
# 1. Indicadores (RN-60 a RN-63)
# =====================================================================

def test_indicadores_de_un_usuario_nuevo(servicio, m):
    i = servicio.indicadores(m.u)
    assert (i.saldo_total, i.total_reservado, i.disponible(), i.disponible_negativo()) == (
        Decimal("100000.00"), Decimal("0"), Decimal("100000.00"), False)


def test_ca10_disponible_negativo_con_aviso(servicio, con_tx, m, mov):
    """CA-10: saldo total 300.000 y reservado 350.000 → disponible −50.000 con aviso; nada se bloquea."""
    mov.registrar(m.u, "INGRESO", m.datos("200000", categoria=m.salario))
    bolsillos = BolsilloServicio(con_tx)
    bolsillos.crear(m.u, DatosBolsillo("Computador"), Decimal("200000"))
    id_b = bolsillos.crear(m.u, DatosBolsillo("Viaje"), Decimal("150000")).bolsillo.id_bolsillo

    i = servicio.indicadores(m.u)
    assert (i.saldo_total, i.total_reservado, i.disponible()) == (
        Decimal("300000.00"), Decimal("350000.00"), Decimal("-50000.00"))
    assert i.disponible_negativo()
    assert i.datos_publicos()["disponible_negativo"] is True

    # Nada se bloquea: se puede seguir reservando y gastando.
    bolsillos.cambiar_valor(m.u, id_b, Decimal("400000"))
    mov.registrar(m.u, "EGRESO", m.datos("1000"))
    assert servicio.indicadores(m.u).disponible() == Decimal("-301000.00")


def test_bolsillos_archivados_no_suman(servicio, con_tx, m):
    """RN-61, RN-49."""
    bolsillos = BolsilloServicio(con_tx)
    bolsillos.crear(m.u, DatosBolsillo("Activo"), Decimal("30000"))
    archivado = bolsillos.crear(m.u, DatosBolsillo("Archivado"), Decimal("50000")).bolsillo.id_bolsillo
    bolsillos.archivar(m.u, archivado)
    assert servicio.indicadores(m.u).total_reservado == Decimal("30000.00")


def test_cuentas_archivadas_no_cambian_el_saldo_total(servicio, con_tx, m):
    """RN-60: una cuenta archivada tiene saldo 0 (RN-12), así que el total no cambia."""
    antes = servicio.indicadores(m.u).saldo_total
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    assert servicio.indicadores(m.u).saldo_total == antes


def test_el_saldo_total_puede_ser_negativo(servicio, m, mov):
    mov.registrar(m.u, "EGRESO", m.datos("150000"))
    i = servicio.indicadores(m.u)
    assert (i.saldo_total, i.disponible_negativo()) == (Decimal("-50000.00"), True)


# =====================================================================
# 2. Periodo (RN-64, RN-53)
# =====================================================================

def test_ca01_desde_el_resumen(servicio, m, mov):
    """CA-01: ingreso 50.000 y egreso 20.000 → balance 30.000; saldo total 130.000."""
    mov.registrar(m.u, "INGRESO", m.datos("50000", categoria=m.salario))
    mov.registrar(m.u, "EGRESO", m.datos("20000"))
    p = noviembre(servicio, m)
    assert (p.ingresos, p.egresos, p.balance()) == (Decimal("50000.00"), Decimal("20000.00"), Decimal("30000.00"))
    assert servicio.indicadores(m.u).saldo_total == Decimal("130000.00")


def test_ca02_desde_el_resumen(servicio, con_tx, m):
    """CA-02: la transferencia no es ingreso ni gasto; su cargo sí es egreso."""
    impuestos = m.impuestos
    TransferenciaServicio(con_tx).registrar(m.u, DatosTransferencia(
        m.nequi, m.nubank, Decimal("200000"), FECHA, cargos=[DatosCargo(Decimal("800"), impuestos)]))
    p = noviembre(servicio, m)
    assert (p.ingresos, p.egresos) == (Decimal("0"), Decimal("800.00"))
    assert categoria(p.categorias_egreso, "Impuestos y comisiones").total() == Decimal("800.00")
    assert servicio.indicadores(m.u).saldo_total == Decimal("99200.00")   # solo baja el cargo


def test_ca11_desde_el_resumen(servicio, con_tx, m, mov):
    """CA-11, RN-53: el ajuste cambia el saldo pero no los egresos; se muestra aparte."""
    mov.registrar(m.u, "INGRESO", m.datos("380000", categoria=m.salario))
    antes = noviembre(servicio, m)
    AjusteServicio(con_tx).ajustar(m.u, m.nequi, Decimal("473500"), "Compras no registradas", FECHA)
    despues = noviembre(servicio, m)
    assert (despues.ingresos, despues.egresos) == (antes.ingresos, antes.egresos)
    assert (despues.ajustes_aumento, despues.ajustes_disminucion) == (Decimal("0"), Decimal("6500.00"))
    assert despues.categorias_egreso == []
    assert servicio.indicadores(m.u).saldo_total == Decimal("473500.00")


def test_anulados_no_cuentan(servicio, m, mov):
    """RN-64: solo VIGENTES."""
    id_mov = mov.registrar(m.u, "EGRESO", m.datos("20000")).movimiento.id_movimiento
    mov.anular(m.u, id_mov)
    p = noviembre(servicio, m)
    assert (p.egresos, p.categorias_egreso) == (Decimal("0"), [])


def test_solo_el_rango_de_fechas_con_los_limites_incluidos(servicio, m, mov):
    for dia, monto in ((date(2026, 10, 31), "1"), (date(2026, 11, 1), "10"),
                       (date(2026, 11, 30), "100"), (date(2026, 12, 1), "1000")):
        mov.registrar(m.u, "EGRESO", m.datos(monto, fecha=dia))
    assert noviembre(servicio, m).egresos == Decimal("110.00")


def test_otro_usuario_no_cuenta(servicio, con_tx, m, mov):
    otro = Mundo(con_tx)
    mov.registrar(otro.u, "INGRESO", otro.datos("999999", categoria=otro.salario))
    p = noviembre(servicio, m)
    assert (p.ingresos, p.categorias_ingreso) == (Decimal("0"), [])
    assert servicio.indicadores(m.u).saldo_total == Decimal("100000.00")


def test_sin_fechas_es_el_mes_actual(servicio, m, mov):
    hoy = date.today()
    mov.registrar(m.u, "EGRESO", m.datos("700", fecha=hoy))
    mov.registrar(m.u, "EGRESO", m.datos("5", fecha=hoy.replace(day=1) - timedelta(days=1)))   # mes anterior
    p = servicio.periodo(m.u)
    assert (p.desde, p.hasta.month, p.egresos) == (hoy.replace(day=1), hoy.month, Decimal("700.00"))
    assert (p.hasta + timedelta(days=1)).day == 1   # último día del mes


def test_fechas_al_reves(servicio, m):
    with pytest.raises(ErrorNegocio, match="no puede ser posterior"):
        servicio.periodo(m.u, date(2026, 12, 1), date(2026, 11, 1))


# =====================================================================
# 3. Totales por categoría (RN-27, CA-12)
# =====================================================================

def test_ca12_subcategorias_consolidadas(servicio, m, mov):
    """CA-12: 20.000 en Alimentación y 30.000 en Mercado → Alimentación 50.000; Mercado 30.000."""
    mov.registrar(m.u, "EGRESO", m.datos("20000", categoria=m.alimentacion))
    mov.registrar(m.u, "EGRESO", m.datos("30000", categoria=m.mercado))
    alimentacion = categoria(noviembre(servicio, m).categorias_egreso, "Alimentación")
    assert (alimentacion.total(), alimentacion.directo) == (Decimal("50000.00"), Decimal("20000.00"))
    assert [(s["nombre"], s["total"]) for s in alimentacion.subcategorias] == [("Mercado", Decimal("30000.00"))]


def test_cada_movimiento_cuenta_una_sola_vez(servicio, m, mov):
    """RN-27: la suma de las raíces es igual al total de egresos (nada se cuenta doble)."""
    for monto, cat in (("20000", m.alimentacion), ("30000", m.mercado), ("8000", m.transporte)):
        mov.registrar(m.u, "EGRESO", m.datos(monto, categoria=cat))
    p = noviembre(servicio, m)
    assert sum(c.total() for c in p.categorias_egreso) == p.egresos == Decimal("58000.00")


def test_ordenadas_de_mayor_a_menor(servicio, m, mov):
    mov.registrar(m.u, "EGRESO", m.datos("8000", categoria=m.transporte))
    mov.registrar(m.u, "EGRESO", m.datos("30000", categoria=m.mercado))
    mov.registrar(m.u, "INGRESO", m.datos("3000000", categoria=m.salario))
    p = noviembre(servicio, m)
    assert [c.nombre for c in p.categorias_egreso] == ["Alimentación", "Transporte"]
    assert [c.nombre for c in p.categorias_ingreso] == ["Salario"]


def test_ca14_una_categoria_desactivada_sigue_sumando(servicio, con_tx, m, mov):
    """CA-14: sus movimientos se conservan, también en los totales."""
    mov.registrar(m.u, "EGRESO", m.datos("20000", categoria=m.mercado))
    CategoriaServicio(con_tx).desactivar(m.u, m.alimentacion)
    assert categoria(noviembre(servicio, m).categorias_egreso, "Alimentación").total() == Decimal("20000.00")


def test_datos_publicos(servicio, m, mov):
    mov.registrar(m.u, "EGRESO", m.datos("30000", categoria=m.mercado))
    datos = noviembre(servicio, m).datos_publicos()
    assert datos["egresos"] == "30000.00"
    assert datos["balance"] == "-30000.00"
    assert datos["categorias"]["egresos"][0] == {
        "id_categoria": m.alimentacion, "nombre": "Alimentación", "total": "30000.00", "porcentaje": "100.0",
        "directo": "0.00", "porcentaje_directo": "0.0",
        "subcategorias": [{"id_categoria": m.mercado, "nombre": "Mercado", "total": "30000.00",
                           "porcentaje": "100.0"}]}


# =====================================================================
# 4. Porcentaje de cada categoría sobre el total de su tipo
# =====================================================================

@pytest.mark.parametrize("parte, total, esperado", [
    ("1", "16", "6.3"),          # 6,25: la mitad se redondea hacia arriba (no 6,2)
    ("2", "3", "66.7"),
    ("1", "3", "33.3"),
    ("30000", "30000", "100.0"),
    ("0", "50000", "0.0"),
    ("0", "0", "0"),             # sin total no hay porcentaje: 0, sin dividir por cero
])
def test_porcentaje_con_decimal_y_un_decimal(parte, total, esperado):
    resultado = porcentaje(Decimal(parte), Decimal(total))
    assert isinstance(resultado, Decimal)
    assert resultado == Decimal(esperado)


def test_porcentajes_de_raices_y_subcategorias(servicio, m, mov):
    """Alimentación 30.000 (10.000 directo + 20.000 en Mercado) y Transporte 10.000: total 40.000."""
    mov.registrar(m.u, "EGRESO", m.datos("10000", categoria=m.alimentacion))
    mov.registrar(m.u, "EGRESO", m.datos("20000", categoria=m.mercado))
    mov.registrar(m.u, "EGRESO", m.datos("10000", categoria=m.transporte))
    egresos = noviembre(servicio, m).datos_publicos()["categorias"]["egresos"]
    alimentacion, transporte = egresos
    assert (alimentacion["porcentaje"], alimentacion["porcentaje_directo"]) == ("75.0", "25.0")
    assert alimentacion["subcategorias"][0]["porcentaje"] == "50.0"   # sobre el total de egresos, no de su raíz
    assert transporte["porcentaje"] == "25.0"


def test_ingresos_y_egresos_tienen_cada_uno_su_total(servicio, m, mov):
    """El porcentaje de un ingreso es sobre los ingresos; el de un egreso, sobre los egresos."""
    mov.registrar(m.u, "INGRESO", m.datos("3000000", categoria=m.salario))
    mov.registrar(m.u, "EGRESO", m.datos("1000", categoria=m.transporte))
    categorias = noviembre(servicio, m).datos_publicos()["categorias"]
    assert categorias["ingresos"][0]["porcentaje"] == "100.0"
    assert categorias["egresos"][0]["porcentaje"] == "100.0"


def test_porcentajes_redondeados(servicio, m, mov):
    """Tres tercios: 33,3 cada uno. Por el redondeo pueden no sumar exactamente 100."""
    for cat in (m.alimentacion, m.transporte, m.impuestos):
        mov.registrar(m.u, "EGRESO", m.datos("1000", categoria=cat))
    egresos = noviembre(servicio, m).datos_publicos()["categorias"]["egresos"]
    assert [c["porcentaje"] for c in egresos] == ["33.3", "33.3", "33.3"]


# =====================================================================
# 5. Resumen mensual (gráfico de ingresos y egresos)
# =====================================================================

MEDIADOS_DE_NOVIEMBRE = date(2026, 11, 15)


def mensual(servicio, m, meses=6, referencia=MEDIADOS_DE_NOVIEMBRE):
    return {t.mes.strftime("%Y-%m"): (t.ingresos, t.egresos) for t in servicio.mensual(m.u, meses, referencia)}


def test_mensual_trae_todos_los_meses_aunque_esten_vacios(servicio, m):
    totales = servicio.mensual(m.u, 6, MEDIADOS_DE_NOVIEMBRE)
    assert [t.mes for t in totales] == [date(2026, mes, 1) for mes in range(6, 12)]   # junio a noviembre
    assert all((t.ingresos, t.egresos, t.balance()) == (0, 0, 0) for t in totales)


def test_mensual_suma_cada_mes_con_sus_limites(servicio, m, mov):
    """RN-64: el primer y el último día de cada mes cuentan en su mes; lo de fuera del rango, no."""
    for dia, monto in ((date(2026, 5, 31), "1"),        # antes de junio: fuera
                       (date(2026, 6, 1), "10"),        # primer día del rango
                       (date(2026, 9, 30), "100"),      # último día de septiembre
                       (date(2026, 10, 1), "1000"),
                       (date(2026, 11, 30), "10000"),   # último día del rango
                       (date(2026, 12, 1), "100000")):  # después de noviembre: fuera
        mov.registrar(m.u, "EGRESO", m.datos(monto, fecha=dia))
    mov.registrar(m.u, "INGRESO", m.datos("50000", categoria=m.salario, fecha=date(2026, 11, 1)))
    assert mensual(servicio, m) == {
        "2026-06": (0, Decimal("10.00")), "2026-07": (0, 0), "2026-08": (0, 0),
        "2026-09": (0, Decimal("100.00")), "2026-10": (0, Decimal("1000.00")),
        "2026-11": (Decimal("50000.00"), Decimal("10000.00")),
    }


def test_mensual_solo_vigentes_sin_transferencias_ni_ajustes(servicio, con_tx, m, mov):
    """RN-64 y RN-53: el anulado, la transferencia y el ajuste no cuentan; el cargo sí (es egreso, D-05)."""
    anulado = mov.registrar(m.u, "EGRESO", m.datos("20000")).movimiento.id_movimiento
    mov.anular(m.u, anulado)
    TransferenciaServicio(con_tx).registrar(m.u, DatosTransferencia(
        m.nequi, m.nubank, Decimal("200000"), FECHA, cargos=[DatosCargo(Decimal("800"), m.impuestos)]))
    AjusteServicio(con_tx).ajustar(m.u, m.nequi, Decimal("5000"), "Cuadre con el banco", FECHA)
    assert mensual(servicio, m)["2026-11"] == (0, Decimal("800.00"))


def test_mensual_otro_usuario_no_cuenta(servicio, con_tx, m, mov):
    otro = Mundo(con_tx)
    mov.registrar(otro.u, "INGRESO", otro.datos("999999", categoria=otro.salario))
    assert mensual(servicio, m)["2026-11"] == (0, 0)


def test_mensual_cruza_el_cambio_de_anio(servicio, m, mov):
    mov.registrar(m.u, "EGRESO", m.datos("300", fecha=date(2026, 12, 24)))
    mov.registrar(m.u, "EGRESO", m.datos("700", fecha=date(2027, 1, 2)))
    assert mensual(servicio, m, 3, date(2027, 2, 10)) == {
        "2026-12": (0, Decimal("300.00")), "2027-01": (0, Decimal("700.00")), "2027-02": (0, 0)}


def test_mensual_un_solo_mes_y_sin_referencia_es_el_actual(servicio, m):
    totales = servicio.mensual(m.u, 1)
    assert [t.mes for t in totales] == [date.today().replace(day=1)]


@pytest.mark.parametrize("meses", [0, 25, -3])
def test_mensual_meses_fuera_de_rango(servicio, m, meses):
    with pytest.raises(ErrorNegocio, match="entre 1 y 24"):
        servicio.mensual(m.u, meses, MEDIADOS_DE_NOVIEMBRE)


def test_mensual_datos_publicos(servicio, m, mov):
    mov.registrar(m.u, "INGRESO", m.datos("50000", categoria=m.salario))
    mov.registrar(m.u, "EGRESO", m.datos("80000.50"))
    noviembre_ = servicio.mensual(m.u, 1, MEDIADOS_DE_NOVIEMBRE)[0]
    assert noviembre_.datos_publicos() == {
        "mes": "2026-11", "ingresos": "50000.00", "egresos": "80000.50", "balance": "-30000.50"}


# =====================================================================
# 6. API GET /api/resumen y GET /api/resumen/mensual
# =====================================================================

@pytest.fixture
def api(cliente_api):
    correo = f"api.{uuid.uuid4().hex[:10]}@prueba.example"
    cliente_api.post("/api/registro", headers=ENCABEZADOS,
                     json={"nombre": "Ana", "correo": correo, "clave": "clave-segura-123"})
    cliente_api.post("/api/cuentas", headers=ENCABEZADOS,
                     json={"nombre": "Nequi", "tipo": "OTRA", "saldo_inicial": "300000"})
    cliente_api.post("/api/bolsillos", headers=ENCABEZADOS, json={"nombre": "Viaje", "valor": "350000"})
    return cliente_api


def test_api_resumen(api):
    r = api.get("/api/resumen?desde=2026-11-01&hasta=2026-11-30")
    assert r.status_code == 200
    datos = r.get_json()
    assert datos["indicadores"] == {"saldo_total": "300000.00", "total_reservado": "350000.00",
                                    "disponible": "-50000.00", "disponible_negativo": True}
    assert datos["periodo"]["desde"] == "2026-11-01"
    assert datos["periodo"]["ajustes"] == {"aumentos": "0.00", "disminuciones": "0.00"}
    assert datos["periodo"]["categorias"] == {"ingresos": [], "egresos": []}


def test_api_sin_fechas_usa_el_mes_actual(api):
    assert api.get("/api/resumen").get_json()["periodo"]["desde"] == date.today().replace(day=1).isoformat()


@pytest.mark.parametrize("consulta, mensaje", [
    ("desde=noviembre", "AAAA-MM-DD"),
    ("desde=2026-12-01&hasta=2026-11-01", "no puede ser posterior"),
])
def test_api_fechas_invalidas(api, consulta, mensaje):
    r = api.get(f"/api/resumen?{consulta}")
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


def test_api_sin_sesion(cliente_api):
    assert cliente_api.get("/api/resumen").status_code == 401


def test_api_resumen_trae_porcentajes(api):
    api.post("/api/movimientos", headers=ENCABEZADOS, json={
        "tipo": "EGRESO", "id_cuenta": _id_cuenta(api), "id_categoria": _id_categoria(api, "Transporte"),
        "monto": "12000", "fecha": "2026-11-05"})
    egresos = api.get("/api/resumen?desde=2026-11-01&hasta=2026-11-30").get_json()["periodo"]["categorias"]["egresos"]
    assert [(c["nombre"], c["total"], c["porcentaje"]) for c in egresos] == [("Transporte", "12000.00", "100.0")]


def test_api_mensual_por_defecto_seis_meses_hasta_el_actual(api):
    r = api.get("/api/resumen/mensual")
    assert r.status_code == 200
    meses = r.get_json()["meses"]
    assert len(meses) == 6
    assert meses[-1]["mes"] == date.today().strftime("%Y-%m")
    assert meses[0] == {"mes": meses[0]["mes"], "ingresos": "0.00", "egresos": "0.00", "balance": "0.00"}


def test_api_mensual_con_meses(api):
    assert len(api.get("/api/resumen/mensual?meses=12").get_json()["meses"]) == 12


@pytest.mark.parametrize("consulta, mensaje", [
    ("meses=0", "entre 1 y 24"),
    ("meses=25", "entre 1 y 24"),
    ("meses=seis", "número entero"),
])
def test_api_mensual_meses_invalidos(api, consulta, mensaje):
    r = api.get(f"/api/resumen/mensual?{consulta}")
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


def test_api_mensual_sin_sesion(cliente_api):
    assert cliente_api.get("/api/resumen/mensual").status_code == 401


def _id_cuenta(api) -> int:
    return api.get("/api/cuentas").get_json()["cuentas"][0]["id_cuenta"]


def _id_categoria(api, nombre: str) -> int:
    ramas = api.get("/api/categorias?tipo=EGRESO").get_json()["categorias"]
    return next(r["id_categoria"] for r in ramas if r["nombre"] == nombre)
