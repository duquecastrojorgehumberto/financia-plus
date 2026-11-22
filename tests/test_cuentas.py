"""Pruebas de cuentas (Tarea 8: RF-02, RF-11; RN-06, RN-10 a RN-14; CA-01, CA-15).

Qué verifican
    * El saldo calculado sigue la fórmula de REGLAS_NEGOCIO.md, sección 2.
    * Crear, editar, archivar (solo con saldo 0) y reactivar, con sus reglas.
    * Que archivar bloquea la fila de la cuenta: mientras tanto, nadie puede
      registrar un movimiento en ella (D-20).
    * La API /api/cuentas: sesión obligatoria, dinero como texto, 404 para
      cuentas ajenas.

Los movimientos se insertan aquí con SQL directo, porque el servicio de
movimientos todavía no existe (Tarea 10).

Todas usan con_tx o cliente_api (conftest.py): no dejan datos en la base.
La prueba del bloqueo necesita datos confirmados en la base; los crea con el
rol dueño y los borra al terminar.
"""

import uuid
from datetime import date
from decimal import Decimal

import psycopg
import pytest
from psycopg import errors

from app.errores import ErrorNegocio, NoEncontrado
from app.servicios.autenticacion import AutenticacionServicio
from app.servicios.cuentas import CuentaServicio
from conftest import url_app_en_base_de_pruebas

ENCABEZADOS = {"X-Requested-With": "financia"}
FECHA = date(2026, 11, 1)


# =====================================================================
# Utilidades
# =====================================================================

def nuevo_usuario(con) -> int:
    """Registra un usuario con el servicio real: así tiene sus categorías por defecto."""
    correo = f"cuentas.{uuid.uuid4().hex[:10]}@prueba.example"
    return AutenticacionServicio(con).registrar("Ana", correo, "clave-segura-123").id_usuario


def id_categoria(con, id_usuario, tipo) -> int:
    return con.execute(
        "SELECT id_categoria FROM categoria WHERE id_usuario = %s AND tipo = %s ORDER BY id_categoria LIMIT 1",
        (id_usuario, tipo),
    ).fetchone()["id_categoria"]


def movimiento(con, id_usuario, tipo, id_cuenta, monto, *, destino=None, estado="VIGENTE"):
    """Inserta un movimiento válido del tipo pedido. Devuelve su id."""
    categoria = id_categoria(con, id_usuario, tipo) if tipo in ("INGRESO", "EGRESO") else None
    descripcion = "Ajuste de prueba" if tipo.startswith("AJUSTE") else None
    return con.execute(
        """
        INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_cuenta_destino, id_categoria,
                                monto, fecha, descripcion, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id_movimiento
        """,
        (id_usuario, tipo, id_cuenta, destino, categoria, Decimal(monto), FECHA, descripcion, estado),
    ).fetchone()["id_movimiento"]


@pytest.fixture
def u(con_tx):
    return nuevo_usuario(con_tx)


@pytest.fixture
def servicio(con_tx):
    return CuentaServicio(con_tx)


def crear(servicio, u, nombre="Nequi", tipo="BILLETERA_DIGITAL", saldo="0"):
    return servicio.crear(u, nombre, tipo, Decimal(saldo)).cuenta.id_cuenta


# =====================================================================
# 1. Crear
# =====================================================================

def test_crear_cuenta(servicio, u):
    """RF-02, RN-10: la cuenta nueva está activa y su saldo es el saldo inicial."""
    c = servicio.crear(u, "  Nequi  ", "BILLETERA_DIGITAL", Decimal("150000.50"))
    assert c.cuenta.nombre == "Nequi"
    assert c.cuenta.activa
    assert c.saldo == Decimal("150000.50")
    assert c.datos_publicos()["saldo"] == "150000.50"


@pytest.mark.parametrize("nombre, tipo, saldo, mensaje", [
    ("   ", "AHORROS", "0", "nombre de la cuenta es obligatorio"),
    ("Nequi", "TARJETA_CREDITO", "0", "tipo de cuenta no es válido"),
    ("Nequi", "ahorros", "0", "tipo de cuenta no es válido"),
    ("Nequi", "AHORROS", "-1", "no puede ser negativo"),
    ("Nequi", "AHORROS", "10.001", "máximo 2 decimales"),
    ("Nequi", "AHORROS", "1000000000000", "demasiado grande"),
])
def test_crear_valida_los_datos(servicio, u, nombre, tipo, saldo, mensaje):
    """RN-10 y D-16: datos inválidos se rechazan con un mensaje claro."""
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.crear(u, nombre, tipo, Decimal(saldo))
    assert servicio.listar(u, incluir_archivadas=True) == []


def test_nombre_repetido_entre_activas_sin_importar_mayusculas(servicio, u):
    """MODELO 4.2: el nombre es único entre las cuentas activas (lo garantiza la base)."""
    crear(servicio, u, "Nequi")
    with pytest.raises(ErrorNegocio, match="Ya tiene una cuenta activa con ese nombre"):
        crear(servicio, u, "NEQUI")


def test_nombre_de_una_archivada_se_puede_reutilizar(servicio, u):
    servicio.archivar(u, crear(servicio, u, "Nequi"))
    crear(servicio, u, "Nequi")
    assert len(servicio.listar(u, incluir_archivadas=True)) == 2


def test_otro_usuario_puede_usar_el_mismo_nombre(servicio, con_tx, u):
    crear(servicio, u, "Nequi")
    crear(servicio, nuevo_usuario(con_tx), "Nequi")


# =====================================================================
# 2. Saldo calculado
# =====================================================================

def test_ca01_saldo_con_ingreso_y_egreso(servicio, con_tx, u):
    """CA-01: saldo inicial 100.000 + ingreso 50.000 − egreso 20.000 = 130.000."""
    c = crear(servicio, u, saldo="100000")
    movimiento(con_tx, u, "INGRESO", c, "50000")
    movimiento(con_tx, u, "EGRESO", c, "20000")
    assert servicio.obtener(u, c).saldo == Decimal("130000.00")


def test_saldo_sigue_la_formula_completa(servicio, con_tx, u):
    """RN-11 y REGLAS_NEGOCIO 2: cada tipo de movimiento suma o resta según corresponda."""
    a = crear(servicio, u, "A", saldo="1000")
    b = crear(servicio, u, "B", saldo="500")
    movimiento(con_tx, u, "INGRESO", a, "300")             # A +300
    movimiento(con_tx, u, "EGRESO", a, "100")              # A −100
    movimiento(con_tx, u, "TRANSFERENCIA", a, "250", destino=b)   # A −250, B +250
    movimiento(con_tx, u, "TRANSFERENCIA", b, "50", destino=a)    # B −50,  A +50
    movimiento(con_tx, u, "AJUSTE_AUMENTO", a, "7")        # A +7
    movimiento(con_tx, u, "AJUSTE_DISMINUCION", b, "3")    # B −3

    assert servicio.obtener(u, a).saldo == Decimal("1007.00")   # 1000 + 300 − 100 − 250 + 50 + 7
    assert servicio.obtener(u, b).saldo == Decimal("697.00")    # 500 + 250 − 50 − 3


def test_movimientos_anulados_no_cuentan(servicio, con_tx, u):
    """RN-70: solo los movimientos VIGENTES afectan el saldo."""
    c = crear(servicio, u, saldo="1000")
    movimiento(con_tx, u, "EGRESO", c, "400", estado="ANULADO")
    assert servicio.obtener(u, c).saldo == Decimal("1000.00")


def test_saldo_negativo_se_permite_con_aviso(servicio, con_tx, u):
    """RN-14: el saldo puede ser negativo; no se bloquea, se avisa."""
    c = crear(servicio, u, saldo="100")
    movimiento(con_tx, u, "EGRESO", c, "150")
    cuenta = servicio.obtener(u, c)
    assert cuenta.saldo == Decimal("-50.00")
    assert cuenta.saldo_negativo()
    assert cuenta.datos_publicos()["saldo_negativo"] is True


def test_movimientos_de_otro_usuario_no_afectan_el_saldo(servicio, con_tx, u):
    c = crear(servicio, u, saldo="100")
    otro = nuevo_usuario(con_tx)
    movimiento(con_tx, otro, "INGRESO", crear(servicio, otro, saldo="0"), "999")
    assert servicio.obtener(u, c).saldo == Decimal("100.00")


def test_listar_solo_activas_salvo_que_se_pidan_las_archivadas(servicio, u):
    activa = crear(servicio, u, "Activa")
    archivada = crear(servicio, u, "Archivada")
    servicio.archivar(u, archivada)
    assert [c.cuenta.id_cuenta for c in servicio.listar(u)] == [activa]
    assert {c.cuenta.id_cuenta for c in servicio.listar(u, incluir_archivadas=True)} == {activa, archivada}


# =====================================================================
# 3. Editar
# =====================================================================

def test_editar_nombre_tipo_y_saldo_inicial_sin_movimientos(servicio, u):
    c = crear(servicio, u, saldo="100")
    editada = servicio.editar(u, c, "Bancolombia", "AHORROS", Decimal("250"))
    assert (editada.cuenta.nombre, editada.cuenta.tipo, editada.saldo) == ("Bancolombia", "AHORROS", Decimal("250.00"))


def test_saldo_inicial_no_cambia_si_hay_movimientos(servicio, con_tx, u):
    """RN-13: con movimientos, el saldo inicial queda fijo (se corrige con un ajuste)."""
    c = crear(servicio, u, saldo="100")
    movimiento(con_tx, u, "INGRESO", c, "10")
    with pytest.raises(ErrorNegocio, match="saldo inicial no se puede cambiar"):
        servicio.editar(u, c, "Nequi", "BILLETERA_DIGITAL", Decimal("200"))


def test_con_movimientos_si_se_puede_cambiar_nombre_y_tipo(servicio, con_tx, u):
    """RN-13 solo bloquea el saldo inicial: el resto se puede editar."""
    c = crear(servicio, u, saldo="100")
    movimiento(con_tx, u, "INGRESO", c, "10")
    editada = servicio.editar(u, c, "Nequi Ana", "OTRA", Decimal("100.00"))
    assert editada.cuenta.nombre == "Nequi Ana"


def test_un_movimiento_anulado_tambien_fija_el_saldo_inicial(servicio, con_tx, u):
    """RN-13: un movimiento anulado se puede reactivar (RN-71), así que también cuenta."""
    c = crear(servicio, u, saldo="100")
    movimiento(con_tx, u, "INGRESO", c, "10", estado="ANULADO")
    with pytest.raises(ErrorNegocio, match="saldo inicial no se puede cambiar"):
        servicio.editar(u, c, "Nequi", "BILLETERA_DIGITAL", Decimal("200"))


def test_ser_destino_de_una_transferencia_tambien_fija_el_saldo_inicial(servicio, con_tx, u):
    a = crear(servicio, u, "A", saldo="100")
    b = crear(servicio, u, "B", saldo="0")
    movimiento(con_tx, u, "TRANSFERENCIA", a, "10", destino=b)
    with pytest.raises(ErrorNegocio, match="saldo inicial no se puede cambiar"):
        servicio.editar(u, b, "B", "BILLETERA_DIGITAL", Decimal("5"))


def test_no_se_edita_una_cuenta_archivada(servicio, u):
    """RN-12: archivada, primero se reactiva."""
    c = crear(servicio, u)
    servicio.archivar(u, c)
    with pytest.raises(ErrorNegocio, match="Reactívela"):
        servicio.editar(u, c, "Otro nombre", "OTRA", Decimal("0"))


def test_editar_a_un_nombre_ocupado(servicio, u):
    crear(servicio, u, "Nequi")
    c = crear(servicio, u, "Daviplata")
    with pytest.raises(ErrorNegocio, match="Ya tiene una cuenta activa con ese nombre"):
        servicio.editar(u, c, "nequi", "BILLETERA_DIGITAL", Decimal("0"))


# =====================================================================
# 4. Archivar y reactivar (RN-12, D-20, CA-15)
# =====================================================================

def test_ca15_no_se_archiva_con_saldo(servicio, u):
    """CA-15: con saldo distinto de 0, rechazado con mensaje claro."""
    c = crear(servicio, u, saldo="100")
    with pytest.raises(ErrorNegocio, match="saldo de 100.00"):
        servicio.archivar(u, c)
    assert servicio.obtener(u, c).cuenta.activa


def test_ca15_no_se_archiva_con_saldo_negativo(servicio, con_tx, u):
    c = crear(servicio, u, saldo="0")
    movimiento(con_tx, u, "EGRESO", c, "30")
    with pytest.raises(ErrorNegocio, match="saldo de -30.00"):
        servicio.archivar(u, c)


def test_ca15_con_saldo_cero_si_se_archiva(servicio, con_tx, u):
    """CA-15: saldo calculado 0 (aunque tenga movimientos) → se archiva."""
    c = crear(servicio, u, saldo="100")
    movimiento(con_tx, u, "EGRESO", c, "100")
    archivada = servicio.archivar(u, c)
    assert not archivada.cuenta.activa
    assert archivada.saldo == 0


def test_archivar_dos_veces(servicio, u):
    c = crear(servicio, u)
    servicio.archivar(u, c)
    with pytest.raises(ErrorNegocio, match="ya está archivada"):
        servicio.archivar(u, c)


def test_reactivar(servicio, u):
    c = crear(servicio, u)
    servicio.archivar(u, c)
    assert servicio.reactivar(u, c).cuenta.activa
    with pytest.raises(ErrorNegocio, match="ya está activa"):
        servicio.reactivar(u, c)


def test_reactivar_con_nombre_ocupado(servicio, u):
    """El índice de nombres solo mira las activas: al reactivar puede chocar."""
    c = crear(servicio, u, "Nequi")
    servicio.archivar(u, c)
    crear(servicio, u, "Nequi")
    with pytest.raises(ErrorNegocio, match="Cámbiele el nombre"):
        servicio.reactivar(u, c)


# =====================================================================
# 5. Cuentas de otro usuario (RN-06)
# =====================================================================

@pytest.mark.parametrize("accion", ["obtener", "editar", "archivar", "reactivar"])
def test_cuenta_ajena_responde_no_encontrado(servicio, con_tx, u, accion):
    """RN-06: una cuenta ajena responde igual que una inexistente, y no se toca."""
    ajena = crear(servicio, nuevo_usuario(con_tx), "Ajena")
    argumentos = {"editar": ("Robada", "OTRA", Decimal("0"))}.get(accion, ())
    with pytest.raises(NoEncontrado):
        getattr(servicio, accion)(u, ajena, *argumentos)
    with pytest.raises(NoEncontrado):
        getattr(servicio, accion)(u, 999_999_999, *argumentos)


# =====================================================================
# 6. Bloqueo de la fila al archivar (D-20)
# =====================================================================

def test_archivar_bloquea_la_cuenta_hasta_terminar(cuenta_confirmada, con_tx):
    """D-20, RN-12: mientras la transacción de archivar no termina, otra conexión no puede
    registrar un movimiento en esa cuenta (espera; aquí se corta a los 0,5 s).

    Cuando con_tx hace ROLLBACK, el bloqueo se libera y la cuenta vuelve a estar activa.
    """
    u, cat, c = cuenta_confirmada
    insertar = ("INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, monto, fecha) "
                "VALUES (%s, 'INGRESO', %s, %s, 1000, %s)")
    try:
        CuentaServicio(con_tx).archivar(u, c)   # con_tx sigue con la transacción abierta: el bloqueo sigue
        with psycopg.connect(url_app_en_base_de_pruebas(), autocommit=True) as otra:
            otra.execute("SET lock_timeout = '500ms'")
            with pytest.raises(errors.LockNotAvailable):
                otra.execute(insertar, (u, c, cat, FECHA))
    finally:
        con_tx.rollback()   # libera el bloqueo antes de que el fixture borre los datos

    # Liberado el bloqueo, el mismo INSERT entra sin esperar.
    with psycopg.connect(url_app_en_base_de_pruebas(), autocommit=True) as otra:
        otra.execute("SET lock_timeout = '500ms'")
        otra.execute(insertar, (u, c, cat, FECHA))


# =====================================================================
# 7. API /api/cuentas
# =====================================================================

@pytest.fixture
def api(cliente_api):
    """Cliente con un usuario recién registrado y su sesión iniciada."""
    r = cliente_api.post("/api/registro", headers=ENCABEZADOS, json={
        "nombre": "Ana", "correo": f"api.{uuid.uuid4().hex[:10]}@prueba.example", "clave": "clave-segura-123"})
    assert r.status_code == 201
    return cliente_api


def test_api_crear_y_ver(api):
    r = api.post("/api/cuentas", headers=ENCABEZADOS,
                 json={"nombre": "Nequi", "tipo": "BILLETERA_DIGITAL", "saldo_inicial": "150000.50"})
    assert r.status_code == 201
    cuenta = r.get_json()["cuenta"]
    assert cuenta["saldo"] == "150000.50"
    assert cuenta["saldo_inicial"] == "150000.50"
    assert cuenta["saldo_negativo"] is False
    assert cuenta["activa"] is True

    r = api.get(f"/api/cuentas/{cuenta['id_cuenta']}")
    assert r.status_code == 200
    assert r.get_json()["cuenta"]["nombre"] == "Nequi"


def test_api_saldo_inicial_es_opcional_al_crear(api):
    r = api.post("/api/cuentas", headers=ENCABEZADOS, json={"nombre": "Efectivo", "tipo": "EFECTIVO"})
    assert r.get_json()["cuenta"]["saldo"] == "0.00"


def test_api_dinero_como_numero_json_es_rechazado(api):
    """RNF-08: el dinero viaja como texto; un número JSON (float) se rechaza."""
    r = api.post("/api/cuentas", headers=ENCABEZADOS,
                 json={"nombre": "Nequi", "tipo": "OTRA", "saldo_inicial": 150000.5})
    assert r.status_code == 400
    assert "no es texto" in r.get_json()["error"]


@pytest.mark.parametrize("valor", ["abc", "NaN", "Infinity", ""])
def test_api_dinero_que_no_es_numero(api, valor):
    r = api.post("/api/cuentas", headers=ENCABEZADOS,
                 json={"nombre": "Nequi", "tipo": "OTRA", "saldo_inicial": valor})
    assert r.status_code == 400


def test_api_listar_editar_archivar_y_reactivar(api):
    id_cuenta = api.post("/api/cuentas", headers=ENCABEZADOS,
                         json={"nombre": "Nequi", "tipo": "OTRA", "saldo_inicial": "100"}).get_json()["cuenta"]["id_cuenta"]

    r = api.post(f"/api/cuentas/{id_cuenta}/archivar", headers=ENCABEZADOS, json={})
    assert r.status_code == 400
    assert "saldo de 100.00" in r.get_json()["error"]

    r = api.put(f"/api/cuentas/{id_cuenta}", headers=ENCABEZADOS,
                json={"nombre": "Nequi Ana", "tipo": "BILLETERA_DIGITAL", "saldo_inicial": "0"})
    assert r.status_code == 200
    assert r.get_json()["cuenta"]["saldo"] == "0.00"

    assert api.post(f"/api/cuentas/{id_cuenta}/archivar", headers=ENCABEZADOS, json={}).status_code == 200
    assert api.get("/api/cuentas").get_json()["cuentas"] == []
    assert len(api.get("/api/cuentas?archivadas=1").get_json()["cuentas"]) == 1

    r = api.post(f"/api/cuentas/{id_cuenta}/reactivar", headers=ENCABEZADOS, json={})
    assert r.get_json()["cuenta"]["activa"] is True


def test_api_cuenta_ajena_responde_404(api, con_tx):
    """RN-06: el usuario de la sesión no ve ni toca cuentas de otro."""
    otro = nuevo_usuario(con_tx)
    ajena = CuentaServicio(con_tx).crear(otro, "Ajena", "OTRA", Decimal("0")).cuenta.id_cuenta
    assert api.get(f"/api/cuentas/{ajena}").status_code == 404
    r = api.put(f"/api/cuentas/{ajena}", headers=ENCABEZADOS,
                json={"nombre": "Robada", "tipo": "OTRA", "saldo_inicial": "0"})
    assert r.status_code == 404
    assert r.get_json() == {"error": "No se encontró la cuenta."}
    assert api.post(f"/api/cuentas/{ajena}/archivar", headers=ENCABEZADOS, json={}).status_code == 404


def test_api_id_usuario_del_cuerpo_se_ignora(api, con_tx):
    """RN-05: aunque el cuerpo traiga otro id_usuario, la cuenta es del usuario de la sesión."""
    otro = nuevo_usuario(con_tx)
    r = api.post("/api/cuentas", headers=ENCABEZADOS,
                 json={"nombre": "Nequi", "tipo": "OTRA", "id_usuario": otro})
    id_cuenta = r.get_json()["cuenta"]["id_cuenta"]
    dueno = con_tx.execute("SELECT id_usuario FROM cuenta WHERE id_cuenta = %s", (id_cuenta,)).fetchone()["id_usuario"]
    assert dueno != otro
    assert dueno == api.get("/api/sesion").get_json()["usuario"]["id_usuario"]


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/api/cuentas"),
    ("post", "/api/cuentas"),
    ("get", "/api/cuentas/1"),
    ("put", "/api/cuentas/1"),
    ("post", "/api/cuentas/1/archivar"),
    ("post", "/api/cuentas/1/reactivar"),
])
def test_api_sin_sesion_responde_401(cliente_api, metodo, ruta):
    r = getattr(cliente_api, metodo)(ruta, headers=ENCABEZADOS, json={})
    assert r.status_code == 401
