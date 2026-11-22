"""Pruebas del archivo de datos de prueba (Tarea 15): db/semillas/datos_prueba.sql.

Qué verifican
    Que el archivo se carga sin errores con el rol de la aplicación y que cada
    resultado que promete su encabezado es cierto, leído con los MISMOS
    servicios que usa la API: saldos, resumen, bolsillos, historial. También
    que sobre esos datos los rechazos (CA-03, CA-05, CA-06, CA-08, CA-15)
    funcionan, y que se puede iniciar sesión con los usuarios de demostración.

Cómo dejan la base como estaba
    El archivo se ejecuta dentro de la transacción de con_tx y se deshace con
    ROLLBACK al terminar cada prueba.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.errores import ErrorNegocio, NoEncontrado
from app.servicios.autenticacion import AutenticacionServicio
from app.servicios.bolsillos import BolsilloServicio
from app.servicios.categorias import CategoriaServicio
from app.servicios.categorias_por_defecto import CATEGORIAS_POR_DEFECTO
from app.servicios.cuentas import CuentaServicio
from app.servicios.movimientos import DatosMovimiento, FiltroHistorial, MovimientoServicio
from app.servicios.resumen import ResumenServicio
from app.servicios.transferencias import DatosCargo, DatosTransferencia, TransferenciaServicio
from scripts.cargar_datos_prueba import CORREOS, sql_sin_transaccion

CLAVE_DEMO = "demo-financia-2026"
NOVIEMBRE = (date(2026, 11, 1), date(2026, 11, 30))


@pytest.fixture
def demo(con_tx):
    """Carga el archivo y devuelve {"ana": id_usuario, "beto": ..., "carla": ...}."""
    con_tx.execute(sql_sin_transaccion())
    filas = con_tx.execute("SELECT id_usuario, correo FROM usuario WHERE correo = ANY(%s)", (list(CORREOS),)).fetchall()
    return {f["correo"].split("@")[0]: f["id_usuario"] for f in filas}


def saldos(con, id_usuario) -> dict[str, Decimal]:
    return {c.cuenta.nombre: c.saldo for c in CuentaServicio(con).listar(id_usuario, incluir_archivadas=True)}


def id_por_nombre(con, tabla_servicio, id_usuario, nombre):
    """Busca un id por nombre en las cuentas, categorías o bolsillos del usuario."""
    if tabla_servicio == "cuenta":
        return next(c.cuenta.id_cuenta for c in CuentaServicio(con).listar(id_usuario, True) if c.cuenta.nombre == nombre)
    if tabla_servicio == "bolsillo":
        return next(b.bolsillo.id_bolsillo for b in BolsilloServicio(con).listar(id_usuario, True) if b.bolsillo.nombre == nombre)
    return con.execute("SELECT id_categoria FROM categoria WHERE id_usuario = %s AND nombre = %s",
                       (id_usuario, nombre)).fetchone()["id_categoria"]


# =====================================================================
# 1. Usuarios y categorías
# =====================================================================

def test_tres_usuarios_que_pueden_iniciar_sesion(con_tx, demo):
    assert set(demo) == {"ana", "beto", "carla"}
    for correo in CORREOS:
        assert AutenticacionServicio(con_tx).iniciar_sesion(correo, CLAVE_DEMO).correo == correo


def test_las_categorias_por_defecto_son_las_de_rn26(con_tx, demo):
    """El archivo repite la lista de app/servicios/categorias_por_defecto.py: deben coincidir."""
    esperado = {(tipo, raiz, tuple(sorted(subs)))
                for tipo, lista in CATEGORIAS_POR_DEFECTO.items() for raiz, subs in lista}
    for nombre, id_usuario in demo.items():
        arbol = CategoriaServicio(con_tx).listar_arbol(id_usuario)   # solo activas: Mascotas no aparece
        obtenido = {(str(r.raiz.tipo), r.raiz.nombre, tuple(sorted(s.nombre for s in r.subcategorias))) for r in arbol}
        assert obtenido == esperado, nombre


# =====================================================================
# 2. Ana: saldos, resumen y criterios con datos
# =====================================================================

def test_saldos_de_ana(con_tx, demo):
    """CA-01, CA-02, CA-04, CA-11, CA-13, CA-15."""
    assert saldos(con_tx, demo["ana"]) == {
        "Efectivo": Decimal("130000.00"), "Nequi": Decimal("229200.00"), "Nubank": Decimal("200000.00"),
        "Bancolombia": Decimal("473500.00"), "Daviplata": Decimal("0.00")}


def test_indicadores_de_ana(con_tx, demo):
    i = ResumenServicio(con_tx).indicadores(demo["ana"])
    assert (i.saldo_total, i.total_reservado, i.disponible(), i.disponible_negativo()) == (
        Decimal("1032700.00"), Decimal("350000.00"), Decimal("682700.00"), False)


def test_resumen_de_noviembre_de_ana(con_tx, demo):
    """RN-64, RN-53, CA-12."""
    p = ResumenServicio(con_tx).periodo(demo["ana"], *NOVIEMBRE)
    assert (p.ingresos, p.egresos, p.ajustes_disminucion) == (Decimal("50000.00"), Decimal("90800.00"), Decimal("6500.00"))
    totales = {c.nombre: c.total() for c in p.categorias_egreso}
    assert totales == {"Alimentación": Decimal("50000.00"), "Mascotas": Decimal("40000.00"),
                       "Impuestos y comisiones": Decimal("800.00")}
    alimentacion = next(c for c in p.categorias_egreso if c.nombre == "Alimentación")
    assert (alimentacion.directo, alimentacion.subcategorias[0]["nombre"]) == (Decimal("20000.00"), "Mercado")


def test_ca13_el_taxi_anulado_sigue_en_el_historial(con_tx, demo):
    anulados = MovimientoServicio(con_tx).historial(demo["ana"], FiltroHistorial(estado="ANULADO"))
    assert {(d.movimiento.tipo, d.movimiento.monto, d.movimiento.descripcion) for d in anulados} == {
        ("EGRESO", Decimal("15000.00"), "Taxi"),
        ("TRANSFERENCIA", Decimal("50000.00"), "Transferencia equivocada"),
        ("EGRESO", Decimal("200.00"), None)}


def test_ca02_y_ca04_las_transferencias_con_sus_cargos(con_tx, demo):
    transferencias = MovimientoServicio(con_tx).historial(demo["ana"], FiltroHistorial(tipo="TRANSFERENCIA"))
    por_estado = {d.movimiento.estado: TransferenciaServicio(con_tx).obtener(demo["ana"], d.movimiento.id_movimiento)
                  for d in transferencias}
    vigente, anulada = por_estado["VIGENTE"], por_estado["ANULADO"]
    assert [(c.nombre_categoria, c.movimiento.monto) for c in vigente.cargos] == [("4×1.000", Decimal("800.00"))]
    assert [c.movimiento.estado for c in anulada.cargos] == ["ANULADO"]   # RN-38


def test_ca14_mascotas_desactivada_con_su_movimiento(con_tx, demo):
    mascotas = id_por_nombre(con_tx, "categoria", demo["ana"], "Mascotas")
    assert not CategoriaServicio(con_tx).obtener(demo["ana"], mascotas).activa
    movs = MovimientoServicio(con_tx).historial(demo["ana"], FiltroHistorial(id_categoria=mascotas))
    assert [(d.movimiento.monto, d.movimiento.estado) for d in movs] == [(Decimal("40000.00"), "VIGENTE")]
    # ...y no se puede usar en uno nuevo.
    nequi = id_por_nombre(con_tx, "cuenta", demo["ana"], "Nequi")
    with pytest.raises(ErrorNegocio, match="desactivada"):
        MovimientoServicio(con_tx).registrar(demo["ana"], "EGRESO", DatosMovimiento(nequi, mascotas, Decimal("1"), date(2026, 11, 21)))


def test_ca07_bolsillo_computador(con_tx, demo):
    id_b = id_por_nombre(con_tx, "bolsillo", demo["ana"], "Computador")
    b = BolsilloServicio(con_tx).obtener(demo["ana"], id_b)
    assert (b.valor_actual, b.progreso_porcentaje()) == (Decimal("350000.00"), Decimal("35.00"))
    assert [v.valor for v in BolsilloServicio(con_tx).historial(demo["ana"], id_b)] == [Decimal("350000.00"), Decimal("0.00")]


def test_bolsillo_archivado_no_suma(con_tx, demo):
    """RN-49, RN-61: Regalos (50.000) está archivado."""
    activos = {b.bolsillo.nombre for b in BolsilloServicio(con_tx).listar(demo["ana"])}
    assert activos == {"Computador"}


def test_ca15_archivar(con_tx, demo):
    """Daviplata ya está archivada con saldo 0; Efectivo tiene saldo y no se puede archivar."""
    cuentas = CuentaServicio(con_tx)
    assert not cuentas.obtener(demo["ana"], id_por_nombre(con_tx, "cuenta", demo["ana"], "Daviplata")).cuenta.activa
    with pytest.raises(ErrorNegocio, match="saldo de 130000.00"):
        cuentas.archivar(demo["ana"], id_por_nombre(con_tx, "cuenta", demo["ana"], "Efectivo"))


# =====================================================================
# 3. Rechazos sobre estos datos (no dejan datos propios)
# =====================================================================

def test_ca03_transferencia_con_cargo_invalido_no_deja_nada(con_tx, demo):
    ana = demo["ana"]
    antes = len(MovimientoServicio(con_tx).historial(ana, FiltroHistorial()))
    nequi, nubank = (id_por_nombre(con_tx, "cuenta", ana, n) for n in ("Nequi", "Nubank"))
    salario = id_por_nombre(con_tx, "categoria", ana, "Salario")
    with pytest.raises(ErrorNegocio, match="es de tipo INGRESO"):
        TransferenciaServicio(con_tx).registrar(ana, DatosTransferencia(
            nequi, nubank, Decimal("1000"), date(2026, 11, 21), cargos=[DatosCargo(Decimal("4"), salario)]))
    assert len(MovimientoServicio(con_tx).historial(ana, FiltroHistorial())) == antes


def test_ca05_egreso_con_salario(con_tx, demo):
    ana = demo["ana"]
    efectivo = id_por_nombre(con_tx, "cuenta", ana, "Efectivo")
    salario = id_por_nombre(con_tx, "categoria", ana, "Salario")
    with pytest.raises(ErrorNegocio, match="es de tipo INGRESO"):
        MovimientoServicio(con_tx).registrar(ana, "EGRESO", DatosMovimiento(efectivo, salario, Decimal("1"), date(2026, 11, 21)))


def test_ca06_ana_no_puede_usar_datos_de_beto(con_tx, demo):
    ana, beto = demo["ana"], demo["beto"]
    nequi_beto = id_por_nombre(con_tx, "cuenta", beto, "Nequi")
    alimentacion_ana = id_por_nombre(con_tx, "categoria", ana, "Alimentación")
    with pytest.raises(NoEncontrado, match="cuenta"):
        MovimientoServicio(con_tx).registrar(ana, "EGRESO", DatosMovimiento(nequi_beto, alimentacion_ana, Decimal("1"), date(2026, 11, 21)))
    with pytest.raises(NoEncontrado):
        CuentaServicio(con_tx).obtener(ana, nequi_beto)
    assert saldos(con_tx, beto) == {"Nequi": Decimal("70000.00")}


def test_ca08_valor_negativo_en_un_bolsillo(con_tx, demo):
    id_b = id_por_nombre(con_tx, "bolsillo", demo["ana"], "Computador")
    with pytest.raises(ErrorNegocio, match="no puede ser negativo"):
        BolsilloServicio(con_tx).cambiar_valor(demo["ana"], id_b, Decimal("-1"))


# =====================================================================
# 4. Carla: CA-09 y CA-10
# =====================================================================

def test_ca09_y_ca10_carla(con_tx, demo):
    carla = demo["carla"]
    assert saldos(con_tx, carla) == {"Nequi": Decimal("200000.00"), "Nubank": Decimal("100000.00")}
    viaje = BolsilloServicio(con_tx).obtener(carla, id_por_nombre(con_tx, "bolsillo", carla, "Viaje"))
    assert viaje.valor_actual == Decimal("200000.00")                      # CA-09
    i = ResumenServicio(con_tx).indicadores(carla)
    assert (i.saldo_total, i.total_reservado, i.disponible(), i.disponible_negativo()) == (
        Decimal("300000.00"), Decimal("350000.00"), Decimal("-50000.00"), True)   # CA-10
