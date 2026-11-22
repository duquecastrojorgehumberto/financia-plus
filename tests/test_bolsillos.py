"""Pruebas de bolsillos y metas (Tarea 13: RF-08 a RF-10, RF-12; RN-40 a RN-49; CA-07 a CA-09).

Qué verifican
    * CA-07: meta de 1.000.000; el usuario escribe 350.000 → valor 350.000,
      progreso 35 %, un registro más en el historial, ningún saldo de cuenta cambia.
    * CA-08: un valor de −1 se rechaza.
    * CA-09: con 200.000 reservados, una transferencia de 100.000 no cambia el bolsillo.
    * Crear con su primer valor en una transacción (RN-45), valor igual sin registro
      (RN-46), el desempate del "más reciente" (D-09), editar, archivar con
      cualquier valor (RN-49), reactivar, otro usuario (RN-06) y la API.

Usan con_tx, cliente_api y Mundo (conftest.py): no dejan datos en la base.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.bolsillos import BolsilloRepositorio
from app.servicios.bolsillos import BolsilloServicio, DatosBolsillo
from app.servicios.movimientos import FiltroHistorial, MovimientoServicio
from app.servicios.transferencias import DatosTransferencia, TransferenciaServicio
from conftest import FECHA, Mundo

ENCABEZADOS = {"X-Requested-With": "financia"}


@pytest.fixture
def m(con_tx):
    return Mundo(con_tx)


@pytest.fixture
def servicio(con_tx):
    return BolsilloServicio(con_tx)


def meta(nombre="Computador", monto="1000000", fecha=None, descripcion=None):
    return DatosBolsillo(nombre=nombre, descripcion=descripcion,
                         monto_objetivo=Decimal(monto) if monto else None, fecha_objetivo=fecha)


def generico(nombre="Emergencias", descripcion=None):
    return DatosBolsillo(nombre=nombre, descripcion=descripcion)


# =====================================================================
# 1. Crear (RN-41, RN-45)
# =====================================================================

def test_crear_generico_con_valor_cero(servicio, m):
    """RN-45: el primer registro del historial es 0 si no se indica otro valor."""
    b = servicio.crear(m.u, generico(descripcion="  Para imprevistos  "))
    assert (b.bolsillo.es_meta(), b.valor_actual, b.progreso_porcentaje()) == (False, Decimal("0.00"), None)
    assert b.bolsillo.descripcion == "Para imprevistos"
    assert [v.valor for v in servicio.historial(m.u, b.bolsillo.id_bolsillo)] == [Decimal("0.00")]


def test_crear_meta_con_valor_inicial(servicio, m):
    b = servicio.crear(m.u, meta(fecha=date(2027, 6, 30)), Decimal("100000"))
    assert b.bolsillo.es_meta()
    assert (b.valor_actual, b.progreso_porcentaje()) == (Decimal("100000.00"), Decimal("10.00"))
    assert b.datos_publicos()["fecha_objetivo"] == "2027-06-30"


def test_crear_es_una_sola_transaccion(servicio, con_tx, m, monkeypatch):
    """RN-45: si falla el primer valor, tampoco queda el bolsillo."""
    def falla(*args, **kwargs):
        raise RuntimeError("falla simulada en el primer valor")

    monkeypatch.setattr(BolsilloRepositorio, "insertar_valor", falla)
    with pytest.raises(RuntimeError):
        servicio.crear(m.u, generico())
    assert con_tx.execute("SELECT count(*) AS n FROM bolsillo WHERE id_usuario = %s", (m.u,)).fetchone()["n"] == 0


@pytest.mark.parametrize("datos, valor, mensaje", [
    (generico("  "), "0", "nombre del bolsillo es obligatorio"),
    (meta(monto="0"), "0", "monto objetivo debe ser mayor que cero"),
    (meta(monto="-5"), "0", "monto objetivo debe ser mayor que cero"),
    (DatosBolsillo("Viaje", fecha_objetivo=date(2027, 1, 1)), "0", "solo se puede indicar si hay un monto objetivo"),
    (generico(), "-1", "no puede ser negativo"),
    (generico(), "10.005", "máximo 2 decimales"),
])
def test_crear_valida_los_datos(servicio, m, datos, valor, mensaje):
    """RN-41 y RN-43."""
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.crear(m.u, datos, Decimal(valor))
    assert servicio.listar(m.u, incluir_archivados=True) == []


def test_nombre_repetido_entre_activos(servicio, m):
    servicio.crear(m.u, generico("Viaje"))
    with pytest.raises(ErrorNegocio, match="Ya tiene un bolsillo activo con ese nombre"):
        servicio.crear(m.u, generico("VIAJE"))


# =====================================================================
# 2. Cambiar el valor (RN-42 a RN-47; CA-07 a CA-09)
# =====================================================================

def test_ca07_meta_al_35_por_ciento_sin_tocar_cuentas(servicio, con_tx, m):
    """CA-07: valor 350.000, progreso 35 %, un registro más, ningún saldo de cuenta cambia."""
    id_b = servicio.crear(m.u, meta(monto="1000000")).bolsillo.id_bolsillo
    saldos = (m.saldo(m.nequi), m.saldo(m.nubank))
    movimientos = len(MovimientoServicio(con_tx).historial(m.u, FiltroHistorial()))

    b, registrado = servicio.cambiar_valor(m.u, id_b, Decimal("350000"))

    assert registrado
    assert (b.valor_actual, b.progreso_porcentaje()) == (Decimal("350000.00"), Decimal("35.00"))
    assert b.datos_publicos()["progreso_porcentaje"] == "35.00"
    assert len(servicio.historial(m.u, id_b)) == 2
    assert (m.saldo(m.nequi), m.saldo(m.nubank)) == saldos                                    # RN-47
    assert len(MovimientoServicio(con_tx).historial(m.u, FiltroHistorial())) == movimientos   # RN-47


def test_ca08_valor_negativo(servicio, m):
    """CA-08, RN-43: rechazado, y el historial no cambia."""
    id_b = servicio.crear(m.u, generico(), Decimal("500")).bolsillo.id_bolsillo
    with pytest.raises(ErrorNegocio, match="no puede ser negativo"):
        servicio.cambiar_valor(m.u, id_b, Decimal("-1"))
    assert [v.valor for v in servicio.historial(m.u, id_b)] == [Decimal("500.00")]


def test_ca09_una_transferencia_no_cambia_el_bolsillo(servicio, con_tx, m):
    """CA-09, RN-39: la reserva no depende de dónde esté el dinero."""
    id_b = servicio.crear(m.u, meta(), Decimal("200000")).bolsillo.id_bolsillo
    TransferenciaServicio(con_tx).registrar(m.u, DatosTransferencia(m.nequi, m.nubank, Decimal("100000"), FECHA))
    b = servicio.obtener(m.u, id_b)
    assert b.valor_actual == Decimal("200000.00")
    assert len(servicio.historial(m.u, id_b)) == 1


def test_valor_igual_no_agrega_registro(servicio, m):
    """RN-46."""
    id_b = servicio.crear(m.u, generico(), Decimal("1000")).bolsillo.id_bolsillo
    _, registrado = servicio.cambiar_valor(m.u, id_b, Decimal("1000.00"))
    assert not registrado
    assert len(servicio.historial(m.u, id_b)) == 1


def test_valor_cero_se_permite(servicio, m):
    """RN-43: cero sí (por ejemplo, después de gastar lo reservado)."""
    id_b = servicio.crear(m.u, generico(), Decimal("1000")).bolsillo.id_bolsillo
    assert servicio.cambiar_valor(m.u, id_b, Decimal("0"))[0].valor_actual == Decimal("0.00")


def test_el_progreso_puede_pasar_de_100(servicio, m):
    """RN-48."""
    id_b = servicio.crear(m.u, meta(monto="300000")).bolsillo.id_bolsillo
    assert servicio.cambiar_valor(m.u, id_b, Decimal("450000"))[0].progreso_porcentaje() == Decimal("150.00")


def test_el_mas_reciente_con_la_misma_hora(servicio, con_tx, m):
    """D-09: todos los valores de esta prueba se guardan en la misma transacción, así que
    tienen el MISMO registrado_en. El valor actual debe ser el último, gracias al desempate
    por id_bolsillo_valor."""
    id_b = servicio.crear(m.u, generico(), Decimal("10")).bolsillo.id_bolsillo
    for valor in ("30", "20", "40", "5"):
        servicio.cambiar_valor(m.u, id_b, Decimal(valor))
    historial = servicio.historial(m.u, id_b)
    assert len({v.registrado_en for v in historial}) == 1                     # misma hora
    assert [v.valor for v in historial] == [Decimal(x) for x in ("5", "40", "20", "30", "10")]
    assert servicio.obtener(m.u, id_b).valor_actual == Decimal("5.00")


# =====================================================================
# 3. Editar, archivar y reactivar (D-08, RN-49)
# =====================================================================

def test_convertir_generico_en_meta_y_volver(servicio, m):
    """D-08: convertir un genérico en meta es llenar el monto objetivo; quitarlo lo vuelve genérico."""
    id_b = servicio.crear(m.u, generico("Viaje"), Decimal("500000")).bolsillo.id_bolsillo
    con_meta = servicio.editar(m.u, id_b, meta("Viaje a Cartagena", "2000000", date(2027, 1, 15)))
    assert (con_meta.bolsillo.nombre, con_meta.progreso_porcentaje()) == ("Viaje a Cartagena", Decimal("25.00"))
    sin_meta = servicio.editar(m.u, id_b, generico("Viaje a Cartagena"))
    assert (sin_meta.bolsillo.es_meta(), sin_meta.bolsillo.fecha_objetivo) == (False, None)
    assert sin_meta.valor_actual == Decimal("500000.00")   # editar no toca el valor


def test_archivar_con_valor(servicio, m):
    """RN-49: se archiva con cualquier valor y conserva su historial."""
    id_b = servicio.crear(m.u, meta(), Decimal("350000")).bolsillo.id_bolsillo
    archivado = servicio.archivar(m.u, id_b)
    assert (archivado.bolsillo.activo, archivado.valor_actual) == (False, Decimal("350000.00"))
    assert servicio.listar(m.u) == []
    assert [b.bolsillo.id_bolsillo for b in servicio.listar(m.u, incluir_archivados=True)] == [id_b]
    assert len(servicio.historial(m.u, id_b)) == 1


@pytest.mark.parametrize("accion", ["editar", "cambiar_valor"])
def test_un_archivado_no_se_edita_ni_cambia_de_valor(servicio, m, accion):
    id_b = servicio.crear(m.u, generico()).bolsillo.id_bolsillo
    servicio.archivar(m.u, id_b)
    argumento = generico("Otro") if accion == "editar" else Decimal("10")
    with pytest.raises(ErrorNegocio, match="Reactívelo"):
        getattr(servicio, accion)(m.u, id_b, argumento)


def test_archivar_y_reactivar_dos_veces(servicio, m):
    id_b = servicio.crear(m.u, generico()).bolsillo.id_bolsillo
    with pytest.raises(ErrorNegocio, match="ya está activo"):
        servicio.reactivar(m.u, id_b)
    servicio.archivar(m.u, id_b)
    with pytest.raises(ErrorNegocio, match="ya está archivado"):
        servicio.archivar(m.u, id_b)
    assert servicio.reactivar(m.u, id_b).bolsillo.activo


def test_reactivar_con_nombre_ocupado(servicio, m):
    id_b = servicio.crear(m.u, generico("Viaje")).bolsillo.id_bolsillo
    servicio.archivar(m.u, id_b)
    servicio.crear(m.u, generico("Viaje"))
    with pytest.raises(ErrorNegocio, match="Cámbiele el nombre"):
        servicio.reactivar(m.u, id_b)


@pytest.mark.parametrize("accion", ["obtener", "historial", "editar", "cambiar_valor", "archivar", "reactivar"])
def test_bolsillo_de_otro_usuario(servicio, con_tx, m, accion):
    """RN-06."""
    otro = Mundo(con_tx)
    ajeno = servicio.crear(otro.u, generico(), Decimal("100")).bolsillo.id_bolsillo
    argumentos = {"editar": (generico("Robado"),), "cambiar_valor": (Decimal("0"),)}.get(accion, ())
    with pytest.raises(NoEncontrado, match="bolsillo"):
        getattr(servicio, accion)(m.u, ajeno, *argumentos)
    assert servicio.obtener(otro.u, ajeno).valor_actual == Decimal("100.00")


# =====================================================================
# 4. API /api/bolsillos
# =====================================================================

@pytest.fixture
def api(cliente_api):
    correo = f"api.{uuid.uuid4().hex[:10]}@prueba.example"
    cliente_api.post("/api/registro", headers=ENCABEZADOS,
                     json={"nombre": "Ana", "correo": correo, "clave": "clave-segura-123"})
    return cliente_api


def test_api_flujo_completo(api):
    r = api.post("/api/bolsillos", headers=ENCABEZADOS,
                 json={"nombre": "Computador", "monto_objetivo": "1000000", "fecha_objetivo": "2027-06-30"})
    assert r.status_code == 201
    b = r.get_json()["bolsillo"]
    assert (b["valor_actual"], b["es_meta"], b["progreso_porcentaje"]) == ("0.00", True, "0.00")

    r = api.post(f"/api/bolsillos/{b['id_bolsillo']}/valor", headers=ENCABEZADOS, json={"valor": "350000"})
    assert r.status_code == 201
    assert (r.get_json()["registrado"], r.get_json()["bolsillo"]["progreso_porcentaje"]) == (True, "35.00")

    r = api.post(f"/api/bolsillos/{b['id_bolsillo']}/valor", headers=ENCABEZADOS, json={"valor": "350000.00"})
    assert (r.status_code, r.get_json()["registrado"]) == (200, False)

    r = api.get(f"/api/bolsillos/{b['id_bolsillo']}")
    assert [v["valor"] for v in r.get_json()["historial"]] == ["350000.00", "0.00"]

    r = api.put(f"/api/bolsillos/{b['id_bolsillo']}", headers=ENCABEZADOS, json={"nombre": "Portátil"})
    assert (r.get_json()["bolsillo"]["nombre"], r.get_json()["bolsillo"]["es_meta"]) == ("Portátil", False)

    assert api.post(f"/api/bolsillos/{b['id_bolsillo']}/archivar", headers=ENCABEZADOS, json={}).status_code == 200
    assert api.get("/api/bolsillos").get_json()["bolsillos"] == []
    assert len(api.get("/api/bolsillos?archivados=1").get_json()["bolsillos"]) == 1
    assert api.post(f"/api/bolsillos/{b['id_bolsillo']}/reactivar", headers=ENCABEZADOS, json={}).status_code == 200


def test_api_ca08_valor_negativo(api):
    id_b = api.post("/api/bolsillos", headers=ENCABEZADOS, json={"nombre": "Viaje"}).get_json()["bolsillo"]["id_bolsillo"]
    r = api.post(f"/api/bolsillos/{id_b}/valor", headers=ENCABEZADOS, json={"valor": "-1"})
    assert r.status_code == 400
    assert "no puede ser negativo" in r.get_json()["error"]


@pytest.mark.parametrize("ruta, metodo, cuerpo, mensaje", [
    ("", "post", {"nombre": "X", "valor": 100}, "no es texto"),
    ("", "post", {"nombre": "X", "id_cuenta": 1}, "Campos no permitidos"),
    ("/{id}", "put", {"nombre": "X", "valor": "5"}, "Campos no permitidos: valor"),
    ("/{id}/valor", "post", {}, "Falta el campo 'valor'"),
])
def test_api_datos_mal_formados(api, ruta, metodo, cuerpo, mensaje):
    """El valor solo se cambia en /valor (RN-44), y un bolsillo no tiene cuenta (D-10)."""
    id_b = api.post("/api/bolsillos", headers=ENCABEZADOS, json={"nombre": "Base"}).get_json()["bolsillo"]["id_bolsillo"]
    r = getattr(api, metodo)("/api/bolsillos" + ruta.format(id=id_b), headers=ENCABEZADOS, json=cuerpo)
    assert r.status_code == 400
    assert mensaje in r.get_json()["error"]


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/api/bolsillos"), ("post", "/api/bolsillos"), ("get", "/api/bolsillos/1"),
    ("put", "/api/bolsillos/1"), ("post", "/api/bolsillos/1/valor"),
    ("post", "/api/bolsillos/1/archivar"), ("post", "/api/bolsillos/1/reactivar"),
])
def test_api_sin_sesion_responde_401(cliente_api, metodo, ruta):
    assert getattr(cliente_api, metodo)(ruta, headers=ENCABEZADOS, json={}).status_code == 401
