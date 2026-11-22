"""Pruebas de ingresos, egresos e historial (Tarea 10: RF-04, RF-05, RF-14, RF-16).

Qué verifican
    * Registrar ingresos y egresos con sus reglas: RN-30, RN-31 (CA-05),
      RN-12 (cuenta archivada), RN-25 (CA-14: categoría desactivada), RN-06 (CA-06).
    * CA-01 con el servicio real.
    * Corregir (RN-72, RN-73), anular (RN-70, CA-13) y reactivar (RN-71).
    * Que lo que todavía es de las Tareas 11 y 12 se rechaza con un mensaje claro
      (anular una transferencia, corregir un cargo).
    * El historial con cada filtro.
    * Bloqueos: si la cuenta se archiva (o la categoría se desactiva) mientras se
      registra un movimiento, el registro espera y lo rechaza (carrera real
      entre dos conexiones).
    * La API /api/movimientos.

Las transferencias, los cargos y los ajustes se insertan con SQL directo: sus
servicios llegan en las Tareas 11 y 12.
"""

import threading
import uuid
from datetime import date
from decimal import Decimal

import psycopg
import pytest

from app.errores import ErrorNegocio, NoEncontrado
from app.servicios.autenticacion import AutenticacionServicio
from app.servicios.categorias import CategoriaServicio
from app.servicios.cuentas import CuentaServicio
from app.servicios.movimientos import DatosMovimiento, FiltroHistorial, MovimientoServicio
from conftest import url_app_en_base_de_pruebas

ENCABEZADOS = {"X-Requested-With": "financia"}
FECHA = date(2026, 11, 1)


# =====================================================================
# Utilidades
# =====================================================================

class Mundo:
    """Un usuario con dos cuentas activas y sus categorías por defecto."""

    def __init__(self, con):
        self.con = con
        correo = f"mov.{uuid.uuid4().hex[:10]}@prueba.example"
        self.u = AutenticacionServicio(con).registrar("Ana", correo, "clave-segura-123").id_usuario
        cuentas = CuentaServicio(con)
        self.nequi = cuentas.crear(self.u, "Nequi", "BILLETERA_DIGITAL", Decimal("100000")).cuenta.id_cuenta
        self.nubank = cuentas.crear(self.u, "Nubank", "AHORROS", Decimal("0")).cuenta.id_cuenta
        arbol = CategoriaServicio(con).listar_arbol(self.u)
        raices = {r.raiz.nombre: r for r in arbol}
        self.salario = raices["Salario"].raiz.id_categoria
        self.alimentacion = raices["Alimentación"].raiz.id_categoria
        self.mercado = next(s.id_categoria for s in raices["Alimentación"].subcategorias if s.nombre == "Mercado")
        self.transporte = raices["Transporte"].raiz.id_categoria
        self.impuestos = raices["Impuestos y comisiones"].raiz.id_categoria

    def datos(self, monto="1000", *, cuenta=None, categoria=None, fecha=FECHA, descripcion=None):
        return DatosMovimiento(id_cuenta=cuenta or self.nequi, id_categoria=categoria or self.alimentacion,
                               monto=Decimal(monto), fecha=fecha, descripcion=descripcion)

    def saldo(self, cuenta=None) -> Decimal:
        return CuentaServicio(self.con).obtener(self.u, cuenta or self.nequi).saldo

    def transferencia(self, monto="200000", estado="VIGENTE") -> int:
        """Transferencia Nequi -> Nubank, con SQL directo (Tarea 11 pendiente)."""
        return self.con.execute(
            "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_cuenta_destino, monto, fecha, estado) "
            "VALUES (%s, 'TRANSFERENCIA', %s, %s, %s, %s, %s) RETURNING id_movimiento",
            (self.u, self.nequi, self.nubank, Decimal(monto), FECHA, estado),
        ).fetchone()["id_movimiento"]

    def cargo(self, id_transferencia, monto="800", estado="VIGENTE") -> int:
        return self.con.execute(
            "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, id_transferencia, monto, fecha, estado) "
            "VALUES (%s, 'EGRESO', %s, %s, %s, %s, %s, %s) RETURNING id_movimiento",
            (self.u, self.nequi, self.impuestos, id_transferencia, Decimal(monto), FECHA, estado),
        ).fetchone()["id_movimiento"]

    def ajuste(self, monto="500") -> int:
        return self.con.execute(
            "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, monto, fecha, descripcion) "
            "VALUES (%s, 'AJUSTE_DISMINUCION', %s, %s, %s, 'Cuadre con el banco') RETURNING id_movimiento",
            (self.u, self.nequi, Decimal(monto), FECHA),
        ).fetchone()["id_movimiento"]


@pytest.fixture
def m(con_tx):
    return Mundo(con_tx)


@pytest.fixture
def servicio(con_tx):
    return MovimientoServicio(con_tx)


def ids(detalles):
    return [d.movimiento.id_movimiento for d in detalles]


# =====================================================================
# 1. Registrar (RF-04, RF-05)
# =====================================================================

def test_ca01_ingreso_y_egreso(servicio, m):
    """CA-01: 100.000 + ingreso 50.000 − egreso 20.000 = 130.000."""
    servicio.registrar(m.u, "INGRESO", m.datos("50000", categoria=m.salario))
    servicio.registrar(m.u, "EGRESO", m.datos("20000"))
    assert m.saldo() == Decimal("130000.00")


def test_registrar_devuelve_el_detalle(servicio, m):
    d = servicio.registrar(m.u, "EGRESO", m.datos("12500.50", categoria=m.mercado, descripcion="  D1  "))
    datos = d.datos_publicos()
    assert datos["tipo"] == "EGRESO"
    assert datos["estado"] == "VIGENTE"
    assert datos["monto"] == "12500.50"
    assert datos["fecha"] == "2026-11-01"
    assert (datos["nombre_cuenta"], datos["nombre_categoria"]) == ("Nequi", "Mercado")
    assert datos["descripcion"] == "D1"


def test_descripcion_vacia_queda_sin_descripcion(servicio, m):
    """RN-30: la descripción es opcional; solo espacios equivale a no tenerla."""
    assert servicio.registrar(m.u, "EGRESO", m.datos(descripcion="   ")).movimiento.descripcion is None


def test_subcategoria_como_categoria(servicio, m):
    """RN-32: se puede usar una raíz o una subcategoría."""
    assert servicio.registrar(m.u, "EGRESO", m.datos(categoria=m.mercado)).movimiento.id_categoria == m.mercado


@pytest.mark.parametrize("monto, mensaje", [
    ("0", "mayor que cero"), ("-5", "mayor que cero"), ("10.005", "máximo 2 decimales"),
    ("1000000000000", "demasiado grande"),
])
def test_monto_invalido(servicio, m, monto, mensaje):
    """RN-30: monto mayor que cero, máximo 2 decimales."""
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.registrar(m.u, "EGRESO", m.datos(monto))


@pytest.mark.parametrize("tipo, mensaje", [
    ("TRANSFERENCIA", "solo se registran ingresos y egresos"),
    ("AJUSTE_AUMENTO", "solo se registran ingresos y egresos"),
    ("egreso", "no es válido"),
])
def test_tipo_no_permitido(servicio, m, tipo, mensaje):
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.registrar(m.u, tipo, m.datos())


def test_ca05_egreso_con_categoria_de_ingreso(servicio, m):
    """CA-05, RN-31: rechazado con un mensaje claro, y no se guarda nada."""
    with pytest.raises(ErrorNegocio, match="'Salario' es de tipo INGRESO"):
        servicio.registrar(m.u, "EGRESO", m.datos(categoria=m.salario))
    assert servicio.historial(m.u, FiltroHistorial()) == []


def test_ca06_cuenta_o_categoria_de_otro_usuario(servicio, con_tx, m):
    """CA-06, RN-06: rechazado como "no encontrado", sin revelar nada del otro usuario."""
    otro = Mundo(con_tx)
    with pytest.raises(NoEncontrado, match="No se encontró la cuenta"):
        servicio.registrar(m.u, "EGRESO", m.datos(cuenta=otro.nequi))
    with pytest.raises(NoEncontrado, match="No se encontró la categoría"):
        servicio.registrar(m.u, "EGRESO", m.datos(categoria=otro.alimentacion))
    assert servicio.historial(m.u, FiltroHistorial()) == []
    assert servicio.historial(otro.u, FiltroHistorial()) == []


def test_cuenta_archivada_no_admite_movimientos(servicio, con_tx, m):
    """RN-12."""
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.registrar(m.u, "INGRESO", m.datos(cuenta=m.nubank, categoria=m.salario))


def test_ca14_categoria_desactivada_no_se_usa_en_un_movimiento_nuevo(servicio, con_tx, m):
    """CA-14, RN-25: la parte que quedó pendiente en la Tarea 9."""
    servicio.registrar(m.u, "EGRESO", m.datos(categoria=m.mercado))
    CategoriaServicio(con_tx).desactivar(m.u, m.alimentacion)   # se lleva también a Mercado
    for categoria in (m.alimentacion, m.mercado):
        with pytest.raises(ErrorNegocio, match="está desactivada"):
            servicio.registrar(m.u, "EGRESO", m.datos(categoria=categoria))
    # El movimiento anterior se conserva y sigue contando.
    assert len(servicio.historial(m.u, FiltroHistorial())) == 1
    assert m.saldo() == Decimal("99000.00")


# =====================================================================
# 2. Corregir (RN-72, RN-73)
# =====================================================================

def test_corregir_todos_los_campos(servicio, m):
    original = servicio.registrar(m.u, "EGRESO", m.datos("1000")).movimiento
    corregido = servicio.corregir(m.u, original.id_movimiento, m.datos(
        "2500", cuenta=m.nubank, categoria=m.transporte, fecha=date(2026, 10, 15), descripcion="Taxi"))
    c = corregido.movimiento
    assert (c.tipo, c.id_cuenta, c.id_categoria, c.monto, c.fecha, c.descripcion) == (
        "EGRESO", m.nubank, m.transporte, Decimal("2500.00"), date(2026, 10, 15), "Taxi")
    assert c.actualizado_en >= original.actualizado_en
    assert m.saldo(m.nequi) == Decimal("100000.00")
    assert m.saldo(m.nubank) == Decimal("-2500.00")


def test_corregir_actualiza_actualizado_en(servicio, con_tx, m):
    """RN-73."""
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    con_tx.execute("UPDATE movimiento SET actualizado_en = '2000-01-01' WHERE id_movimiento = %s", (id_mov,))
    corregido = servicio.corregir(m.u, id_mov, m.datos("5"))
    assert corregido.movimiento.actualizado_en.year > 2000


def test_corregir_a_categoria_de_otro_tipo(servicio, m):
    """RN-31, RN-72: el tipo no cambia, así que la categoría nueva debe ser del mismo tipo."""
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="es de tipo INGRESO"):
        servicio.corregir(m.u, id_mov, m.datos(categoria=m.salario))


def test_corregir_un_anulado(servicio, m):
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    servicio.anular(m.u, id_mov)
    with pytest.raises(ErrorNegocio, match="Reactívelo para corregirlo"):
        servicio.corregir(m.u, id_mov, m.datos("5"))


def test_corregir_con_la_cuenta_archivada(servicio, con_tx, m):
    """RN-12: los movimientos de una cuenta archivada no se corrigen."""
    id_mov = servicio.registrar(m.u, "INGRESO", m.datos("100", cuenta=m.nubank, categoria=m.salario)).movimiento.id_movimiento
    servicio.registrar(m.u, "EGRESO", m.datos("100", cuenta=m.nubank))   # saldo 0 para poder archivar
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="cuenta del movimiento está archivada"):
        servicio.corregir(m.u, id_mov, m.datos("100", cuenta=m.nubank, categoria=m.salario))


def test_corregir_hacia_una_cuenta_archivada(servicio, con_tx, m):
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="no admite movimientos"):
        servicio.corregir(m.u, id_mov, m.datos(cuenta=m.nubank))


def test_corregir_conserva_una_categoria_que_se_desactivo_despues(servicio, con_tx, m):
    """Si la categoría no cambia, se puede corregir el monto aunque ya esté desactivada."""
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos("1000", categoria=m.transporte)).movimiento.id_movimiento
    CategoriaServicio(con_tx).desactivar(m.u, m.transporte)
    assert servicio.corregir(m.u, id_mov, m.datos("1500", categoria=m.transporte)).movimiento.monto == Decimal("1500.00")


def test_corregir_hacia_una_categoria_desactivada(servicio, con_tx, m):
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    CategoriaServicio(con_tx).desactivar(m.u, m.transporte)
    with pytest.raises(ErrorNegocio, match="está desactivada"):
        servicio.corregir(m.u, id_mov, m.datos(categoria=m.transporte))


@pytest.mark.parametrize("que", ["transferencia", "cargo", "ajuste"])
def test_corregir_otros_tipos_se_hace_en_su_propio_registro(servicio, m, que):
    """Tareas 11 y 12: transferencias, cargos y ajustes no se corrigen aquí."""
    t = m.transferencia()
    id_mov = {"transferencia": t, "cargo": m.cargo(t), "ajuste": m.ajuste()}[que]
    with pytest.raises(ErrorNegocio, match="solo se corrigen ingresos y egresos"):
        servicio.corregir(m.u, id_mov, m.datos())


# =====================================================================
# 3. Anular y reactivar (RN-70, RN-71, CA-13)
# =====================================================================

def test_ca13_anular_un_egreso(servicio, m):
    """CA-13: deja de contar; sigue visible en el historial como anulado."""
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos("20000")).movimiento.id_movimiento
    assert m.saldo() == Decimal("80000.00")
    anulado = servicio.anular(m.u, id_mov)
    assert anulado.movimiento.estado == "ANULADO"
    assert m.saldo() == Decimal("100000.00")
    historial = servicio.historial(m.u, FiltroHistorial())
    assert ids(historial) == [id_mov]
    assert historial[0].movimiento.estado == "ANULADO"


def test_reactivar_vuelve_a_contar(servicio, m):
    """RN-71."""
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos("20000")).movimiento.id_movimiento
    servicio.anular(m.u, id_mov)
    assert servicio.reactivar(m.u, id_mov).movimiento.estado == "VIGENTE"
    assert m.saldo() == Decimal("80000.00")


def test_anular_y_reactivar_dos_veces(servicio, m):
    id_mov = servicio.registrar(m.u, "EGRESO", m.datos()).movimiento.id_movimiento
    with pytest.raises(ErrorNegocio, match="ya está vigente"):
        servicio.reactivar(m.u, id_mov)
    servicio.anular(m.u, id_mov)
    with pytest.raises(ErrorNegocio, match="ya está anulado"):
        servicio.anular(m.u, id_mov)


def test_anular_con_la_cuenta_archivada(servicio, con_tx, m):
    """RN-12: archivada, sus movimientos no se anulan ni se reactivan."""
    id_ing = servicio.registrar(m.u, "INGRESO", m.datos("100", cuenta=m.nubank, categoria=m.salario)).movimiento.id_movimiento
    servicio.registrar(m.u, "EGRESO", m.datos("100", cuenta=m.nubank))
    CuentaServicio(con_tx).archivar(m.u, m.nubank)
    with pytest.raises(ErrorNegocio, match="archivada"):
        servicio.anular(m.u, id_ing)


def test_una_transferencia_no_se_anula_aqui(servicio, m):
    """RN-38 (Tarea 11): anularla aquí dejaría sus cargos vigentes."""
    t = m.transferencia()
    with pytest.raises(ErrorNegocio, match="junto con sus cargos"):
        servicio.anular(m.u, t)


def test_un_cargo_si_se_anula_solo(servicio, m):
    """RN-38: un cargo puede anularse sin tocar su transferencia."""
    t = m.transferencia()
    cargo = m.cargo(t)
    servicio.anular(m.u, cargo)
    assert servicio.obtener(m.u, t).movimiento.estado == "VIGENTE"
    assert m.saldo() == Decimal("-100000.00")   # 100.000 − 200.000; el cargo de 800 ya no cuenta


def test_cargo_de_transferencia_anulada_no_se_reactiva(servicio, m):
    t = m.transferencia(estado="ANULADO")
    cargo = m.cargo(t, estado="ANULADO")
    with pytest.raises(ErrorNegocio, match="Reactive primero la transferencia"):
        servicio.reactivar(m.u, cargo)


def test_cargo_de_transferencia_vigente_si_se_reactiva(servicio, m):
    cargo = m.cargo(m.transferencia(), estado="ANULADO")
    assert servicio.reactivar(m.u, cargo).movimiento.estado == "VIGENTE"


def test_un_ajuste_se_anula_y_reactiva(servicio, m):
    """RN-54: el ajuste se puede anular como cualquier movimiento."""
    ajuste = m.ajuste("500")
    assert m.saldo() == Decimal("99500.00")
    servicio.anular(m.u, ajuste)
    assert m.saldo() == Decimal("100000.00")
    servicio.reactivar(m.u, ajuste)
    assert m.saldo() == Decimal("99500.00")


@pytest.mark.parametrize("accion", ["obtener", "anular", "reactivar", "corregir"])
def test_movimiento_ajeno_responde_no_encontrado(servicio, con_tx, m, accion):
    """RN-06."""
    otro = Mundo(con_tx)
    ajeno = servicio.registrar(otro.u, "EGRESO", otro.datos()).movimiento.id_movimiento
    argumentos = (m.datos(),) if accion == "corregir" else ()
    with pytest.raises(NoEncontrado):
        getattr(servicio, accion)(m.u, ajeno, *argumentos)
    assert servicio.obtener(otro.u, ajeno).movimiento.estado == "VIGENTE"


# =====================================================================
# 4. Historial (RF-14)
# =====================================================================

@pytest.fixture
def historial(servicio, m):
    """Seis movimientos variados para probar los filtros."""
    r = lambda tipo, d: servicio.registrar(m.u, tipo, d).movimiento.id_movimiento   # noqa: E731
    h = {
        "salario": r("INGRESO", m.datos("3000000", categoria=m.salario, fecha=date(2026, 10, 30))),
        "mercado": r("EGRESO", m.datos("150000", categoria=m.mercado, fecha=date(2026, 11, 2))),
        "almuerzo": r("EGRESO", m.datos("25000", categoria=m.alimentacion, fecha=date(2026, 11, 5))),
        "taxi": r("EGRESO", m.datos("18000", cuenta=m.nubank, categoria=m.transporte, fecha=date(2026, 11, 5))),
        "transferencia": m.transferencia(),   # 2026-11-01, Nequi -> Nubank
    }
    servicio.anular(m.u, h["almuerzo"])
    return h


def test_historial_completo_del_mas_reciente_al_mas_antiguo(servicio, m, historial):
    """Mismo día: primero el registrado después."""
    assert ids(servicio.historial(m.u, FiltroHistorial())) == [
        historial["taxi"], historial["almuerzo"], historial["mercado"],
        historial["transferencia"], historial["salario"]]


def test_historial_por_fechas(servicio, m, historial):
    filtro = FiltroHistorial(desde=date(2026, 11, 1), hasta=date(2026, 11, 2))
    assert ids(servicio.historial(m.u, filtro)) == [historial["mercado"], historial["transferencia"]]


def test_historial_por_cuenta_incluye_transferencias_que_entran(servicio, m, historial):
    assert ids(servicio.historial(m.u, FiltroHistorial(id_cuenta=m.nubank))) == [
        historial["taxi"], historial["transferencia"]]


def test_historial_por_tipo(servicio, m, historial):
    assert ids(servicio.historial(m.u, FiltroHistorial(tipo="INGRESO"))) == [historial["salario"]]


def test_historial_por_categoria_incluye_subcategorias(servicio, m, historial):
    """Filtrar por Alimentación muestra también lo de Mercado (su subcategoría)."""
    assert ids(servicio.historial(m.u, FiltroHistorial(id_categoria=m.alimentacion))) == [
        historial["almuerzo"], historial["mercado"]]
    assert ids(servicio.historial(m.u, FiltroHistorial(id_categoria=m.mercado))) == [historial["mercado"]]


def test_historial_por_estado(servicio, m, historial):
    assert ids(servicio.historial(m.u, FiltroHistorial(estado="ANULADO"))) == [historial["almuerzo"]]


def test_historial_combina_filtros(servicio, m, historial):
    filtro = FiltroHistorial(tipo="EGRESO", estado="VIGENTE", id_cuenta=m.nequi)
    assert ids(servicio.historial(m.u, filtro)) == [historial["mercado"]]


def test_historial_trae_los_nombres(servicio, m, historial):
    transferencia = servicio.obtener(m.u, historial["transferencia"]).datos_publicos()
    assert (transferencia["nombre_cuenta"], transferencia["nombre_cuenta_destino"]) == ("Nequi", "Nubank")
    assert transferencia["nombre_categoria"] is None


def test_historial_no_muestra_movimientos_de_otro_usuario(servicio, con_tx, m, historial):
    otro = Mundo(con_tx)
    servicio.registrar(otro.u, "EGRESO", otro.datos())
    assert len(servicio.historial(m.u, FiltroHistorial())) == 5
    # Ni siquiera filtrando por una cuenta o categoría del otro usuario.
    assert servicio.historial(m.u, FiltroHistorial(id_cuenta=otro.nequi)) == []
    assert servicio.historial(m.u, FiltroHistorial(id_categoria=otro.alimentacion)) == []


@pytest.mark.parametrize("filtro, mensaje", [
    (FiltroHistorial(desde=date(2026, 12, 1), hasta=date(2026, 11, 1)), "no puede ser posterior"),
    (FiltroHistorial(tipo="GASTO"), "tipo de movimiento no es válido"),
    (FiltroHistorial(estado="BORRADO"), "estado no es válido"),
])
def test_historial_con_filtros_invalidos(servicio, m, filtro, mensaje):
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.historial(m.u, filtro)


# =====================================================================
# 5. Bloqueos entre dos conexiones (RN-12, RN-25)
#
# La carrera que se quiere evitar:
#     A (registrar)                         B (archivar la cuenta)
#     lee la cuenta: activa                 
#                                           la bloquea y la marca archivada
#                                           COMMIT
#     INSERT del movimiento                 -> ¡movimiento en una cuenta archivada!
#
# registrar() lee la cuenta con FOR SHARE. Si B ya la tiene bloqueada, A
# espera a que B termine y entonces lee el valor NUEVO (archivada) y rechaza.
# Las pruebas reproducen la carrera: B bloquea y cambia la fila, A empieza a
# registrar, y B confirma medio segundo después desde otro hilo.
# =====================================================================

def _confirmar_luego(conexion, segundos=0.5):
    hilo = threading.Timer(segundos, conexion.commit)
    hilo.start()
    return hilo


def test_carrera_registrar_mientras_se_archiva_la_cuenta(cuenta_confirmada, con_tx):
    u, cat, c = cuenta_confirmada
    with psycopg.connect(url_app_en_base_de_pruebas()) as b:
        b.execute("SELECT 1 FROM cuenta WHERE id_cuenta = %s FOR UPDATE", (c,))
        b.execute("UPDATE cuenta SET activa = false WHERE id_cuenta = %s", (c,))
        hilo = _confirmar_luego(b)
        try:
            with pytest.raises(ErrorNegocio, match="archivada"):
                MovimientoServicio(con_tx).registrar(u, "INGRESO", DatosMovimiento(c, cat, Decimal("1000"), FECHA))
        finally:
            hilo.join()
            con_tx.rollback()


def test_carrera_registrar_mientras_se_desactiva_la_categoria(cuenta_confirmada, con_tx):
    u, cat, c = cuenta_confirmada
    with psycopg.connect(url_app_en_base_de_pruebas()) as b:
        b.execute("SELECT 1 FROM categoria WHERE id_categoria = %s FOR UPDATE", (cat,))
        b.execute("UPDATE categoria SET activa = false WHERE id_categoria = %s", (cat,))
        hilo = _confirmar_luego(b)
        try:
            with pytest.raises(ErrorNegocio, match="desactivada"):
                MovimientoServicio(con_tx).registrar(u, "INGRESO", DatosMovimiento(c, cat, Decimal("1000"), FECHA))
        finally:
            hilo.join()
            con_tx.rollback()


# =====================================================================
# 6. API /api/movimientos
# =====================================================================

@pytest.fixture
def api(cliente_api, con_tx):
    """Cliente con sesión iniciada; devuelve (cliente, mundo del usuario de la sesión)."""
    correo = f"api.{uuid.uuid4().hex[:10]}@prueba.example"
    r = cliente_api.post("/api/registro", headers=ENCABEZADOS,
                         json={"nombre": "Ana", "correo": correo, "clave": "clave-segura-123"})
    u = r.get_json()["usuario"]["id_usuario"]
    nequi = cliente_api.post("/api/cuentas", headers=ENCABEZADOS, json={
        "nombre": "Nequi", "tipo": "OTRA", "saldo_inicial": "100000"}).get_json()["cuenta"]["id_cuenta"]
    arbol = cliente_api.get("/api/categorias").get_json()["categorias"]
    categoria = {c["nombre"]: c["id_categoria"] for c in arbol}
    return cliente_api, {"u": u, "nequi": nequi, "salario": categoria["Salario"],
                         "alimentacion": categoria["Alimentación"]}


def test_api_registrar_listar_corregir_anular(api):
    cliente, d = api
    r = cliente.post("/api/movimientos", headers=ENCABEZADOS, json={
        "tipo": "EGRESO", "id_cuenta": d["nequi"], "id_categoria": d["alimentacion"],
        "monto": "20000", "fecha": "2026-11-01", "descripcion": "Mercado"})
    assert r.status_code == 201
    mov = r.get_json()["movimiento"]
    assert (mov["monto"], mov["nombre_categoria"], mov["estado"]) == ("20000.00", "Alimentación", "VIGENTE")
    assert cliente.get(f"/api/cuentas/{d['nequi']}").get_json()["cuenta"]["saldo"] == "80000.00"

    r = cliente.get("/api/movimientos?desde=2026-11-01&tipo=EGRESO")
    assert [x["id_movimiento"] for x in r.get_json()["movimientos"]] == [mov["id_movimiento"]]

    r = cliente.put(f"/api/movimientos/{mov['id_movimiento']}", headers=ENCABEZADOS, json={
        "id_cuenta": d["nequi"], "id_categoria": d["alimentacion"], "monto": "25000", "fecha": "2026-11-02"})
    assert r.status_code == 200
    assert (r.get_json()["movimiento"]["monto"], r.get_json()["movimiento"]["descripcion"]) == ("25000.00", None)

    r = cliente.post(f"/api/movimientos/{mov['id_movimiento']}/anular", headers=ENCABEZADOS, json={})
    assert r.get_json()["movimiento"]["estado"] == "ANULADO"
    assert cliente.get(f"/api/cuentas/{d['nequi']}").get_json()["cuenta"]["saldo"] == "100000.00"

    r = cliente.post(f"/api/movimientos/{mov['id_movimiento']}/reactivar", headers=ENCABEZADOS, json={})
    assert r.get_json()["movimiento"]["estado"] == "VIGENTE"


def test_api_corregir_no_acepta_tipo(api):
    """RN-72: el tipo no cambia; si llega, 400."""
    cliente, d = api
    id_mov = cliente.post("/api/movimientos", headers=ENCABEZADOS, json={
        "tipo": "EGRESO", "id_cuenta": d["nequi"], "id_categoria": d["alimentacion"],
        "monto": "100", "fecha": "2026-11-01"}).get_json()["movimiento"]["id_movimiento"]
    r = cliente.put(f"/api/movimientos/{id_mov}", headers=ENCABEZADOS, json={
        "tipo": "INGRESO", "id_cuenta": d["nequi"], "id_categoria": d["salario"],
        "monto": "100", "fecha": "2026-11-01"})
    assert r.status_code == 400
    assert "Campos no permitidos: tipo" in r.get_json()["error"]


@pytest.mark.parametrize("cambio, mensaje", [
    ({"monto": 100}, "no es texto"),
    ({"monto": "cien"}, "debe ser un número"),
    ({"fecha": "01/11/2026"}, "AAAA-MM-DD"),
    ({"fecha": "2026-02-30"}, "AAAA-MM-DD"),
    ({"id_cuenta": "3"}, "número entero"),
    ({"descripcion": 5}, "debe ser texto"),
    ({"id_usuario": 1}, "Campos no permitidos"),
])
def test_api_datos_mal_formados(api, cambio, mensaje):
    cliente, d = api
    cuerpo = {"tipo": "EGRESO", "id_cuenta": d["nequi"], "id_categoria": d["alimentacion"],
              "monto": "100", "fecha": "2026-11-01", **cambio}
    r = cliente.post("/api/movimientos", headers=ENCABEZADOS, json=cuerpo)
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


@pytest.mark.parametrize("consulta, mensaje", [
    ("desde=ayer", "AAAA-MM-DD"),
    ("id_cuenta=abc", "número entero"),
    ("tipo=GASTO", "no es válido"),
])
def test_api_filtros_mal_formados(api, consulta, mensaje):
    cliente, _ = api
    r = cliente.get(f"/api/movimientos?{consulta}")
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


def test_api_ca06_cuenta_ajena_responde_404(api, con_tx):
    """CA-06: no revela si la cuenta existe."""
    cliente, d = api
    otro = Mundo(con_tx)
    r = cliente.post("/api/movimientos", headers=ENCABEZADOS, json={
        "tipo": "EGRESO", "id_cuenta": otro.nequi, "id_categoria": d["alimentacion"],
        "monto": "100", "fecha": "2026-11-01"})
    assert r.status_code == 404
    assert r.get_json() == {"error": "No se encontró la cuenta."}


def test_api_ca05_egreso_con_categoria_de_ingreso(api):
    cliente, d = api
    r = cliente.post("/api/movimientos", headers=ENCABEZADOS, json={
        "tipo": "EGRESO", "id_cuenta": d["nequi"], "id_categoria": d["salario"],
        "monto": "100", "fecha": "2026-11-01"})
    assert r.status_code == 400
    assert "es de tipo INGRESO" in r.get_json()["error"]


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/api/movimientos"),
    ("post", "/api/movimientos"),
    ("get", "/api/movimientos/1"),
    ("put", "/api/movimientos/1"),
    ("post", "/api/movimientos/1/anular"),
    ("post", "/api/movimientos/1/reactivar"),
])
def test_api_sin_sesion_responde_401(cliente_api, metodo, ruta):
    r = getattr(cliente_api, metodo)(ruta, headers=ENCABEZADOS, json={})
    assert r.status_code == 401
