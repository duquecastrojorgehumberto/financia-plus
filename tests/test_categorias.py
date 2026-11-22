"""Pruebas de categorías (Tarea 9: RF-03; RN-06, RN-20 a RN-25; CA-14).

Qué verifican
    * Crear raíces y subcategorías; la subcategoría toma el tipo del padre.
    * Máximo dos niveles (RN-21): la base lo permitiría, el servicio no.
    * Solo cambia el nombre (RN-22); nombres únicos entre hermanas activas (RN-24).
    * Desactivar (RN-25): desactiva también las subcategorías y conserva los
      movimientos (CA-14). Que una categoría desactivada no se pueda usar en un
      movimiento NUEVO lo verificará la Tarea 10, que crea el servicio de movimientos.
    * Reactivar, el árbol con filtros y la API /api/categorias.

Usan con_tx y cliente_api (conftest.py): no dejan datos en la base.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.entidades.categoria import TipoCategoria
from app.errores import ErrorNegocio, NoEncontrado
from app.servicios.autenticacion import AutenticacionServicio
from app.servicios.categorias import CategoriaServicio
from app.servicios.cuentas import CuentaServicio

ENCABEZADOS = {"X-Requested-With": "financia"}


def nuevo_usuario(con) -> int:
    correo = f"categorias.{uuid.uuid4().hex[:10]}@prueba.example"
    return AutenticacionServicio(con).registrar("Ana", correo, "clave-segura-123").id_usuario


@pytest.fixture
def u(con_tx):
    return nuevo_usuario(con_tx)


@pytest.fixture
def servicio(con_tx):
    return CategoriaServicio(con_tx)


def buscar(servicio, u, nombre, tipo="EGRESO"):
    """La rama (raíz) con ese nombre entre las categorías activas del usuario."""
    return next(r for r in servicio.listar_arbol(u, tipo) if r.raiz.nombre == nombre)


# =====================================================================
# 1. Crear
# =====================================================================

def test_crear_raiz(servicio, u):
    c = servicio.crear(u, "  Mascotas  ", "EGRESO")
    assert (c.nombre, c.tipo, c.id_padre, c.activa) == ("Mascotas", TipoCategoria.EGRESO, None, True)


def test_crear_subcategoria_toma_el_tipo_del_padre(servicio, u):
    """RN-23: sin indicar tipo, la subcategoría queda con el del padre."""
    padre = servicio.crear(u, "Mascotas", "EGRESO")
    hija = servicio.crear(u, "Veterinario", id_padre=padre.id_categoria)
    assert hija.tipo == TipoCategoria.EGRESO
    assert hija.id_padre == padre.id_categoria
    assert hija.es_subcategoria()


def test_subcategoria_con_tipo_distinto_al_del_padre(servicio, u):
    padre = servicio.crear(u, "Mascotas", "EGRESO")
    with pytest.raises(ErrorNegocio, match="tipo de su padre"):
        servicio.crear(u, "Venta de cachorros", "INGRESO", id_padre=padre.id_categoria)


def test_no_hay_tercer_nivel(servicio, u):
    """RN-21: el padre debe ser raíz. La base aceptaría un tercer nivel; el servicio no."""
    padre = servicio.crear(u, "Mascotas", "EGRESO")
    hija = servicio.crear(u, "Veterinario", id_padre=padre.id_categoria)
    with pytest.raises(ErrorNegocio, match="Solo hay dos niveles"):
        servicio.crear(u, "Vacunas", id_padre=hija.id_categoria)


def test_padre_desactivado_no_admite_subcategorias(servicio, u):
    padre = servicio.crear(u, "Mascotas", "EGRESO")
    servicio.desactivar(u, padre.id_categoria)
    with pytest.raises(ErrorNegocio, match="padre está desactivada"):
        servicio.crear(u, "Veterinario", id_padre=padre.id_categoria)


@pytest.mark.parametrize("nombre, tipo, mensaje", [
    ("   ", "EGRESO", "nombre de la categoría es obligatorio"),
    ("Mascotas", None, "Indique el tipo"),
    ("Mascotas", "TRANSFERENCIA", "debe ser INGRESO o EGRESO"),
    ("Mascotas", "egreso", "debe ser INGRESO o EGRESO"),
])
def test_crear_valida_los_datos(servicio, u, nombre, tipo, mensaje):
    """RN-20: datos inválidos se rechazan con un mensaje claro."""
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.crear(u, nombre, tipo)


def test_nombre_repetido_entre_raices_del_mismo_tipo(servicio, u):
    """RN-24: 'Alimentación' ya existe entre las raíces de egreso (categorías por defecto)."""
    with pytest.raises(ErrorNegocio, match="Ya existe una categoría activa con ese nombre"):
        servicio.crear(u, "ALIMENTACIÓN", "EGRESO")


def test_mismo_nombre_en_raices_de_distinto_tipo(servicio, u):
    """RN-24: 'Otros' de INGRESO y 'Otros' de EGRESO pueden convivir."""
    servicio.crear(u, "Otros", "INGRESO")
    servicio.crear(u, "Otros", "EGRESO")


def test_mismo_nombre_bajo_padres_distintos(servicio, u):
    """RN-24: la unicidad es entre hermanas, no en todo el árbol."""
    a = servicio.crear(u, "Mascotas", "EGRESO")
    b = servicio.crear(u, "Hijos", "EGRESO")
    servicio.crear(u, "Salud", id_padre=a.id_categoria)
    servicio.crear(u, "Salud", id_padre=b.id_categoria)


def test_nombre_de_una_desactivada_se_puede_reutilizar(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    servicio.desactivar(u, c.id_categoria)
    servicio.crear(u, "Mascotas", "EGRESO")


# =====================================================================
# 2. Renombrar (RN-22)
# =====================================================================

def test_renombrar(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    renombrada = servicio.renombrar(u, c.id_categoria, "Animales")
    assert renombrada.nombre == "Animales"
    assert (renombrada.tipo, renombrada.id_padre) == (c.tipo, c.id_padre)


def test_renombrar_a_un_nombre_ocupado(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    with pytest.raises(ErrorNegocio, match="Ya existe una categoría activa con ese nombre"):
        servicio.renombrar(u, c.id_categoria, "Vivienda")


def test_no_se_renombra_una_desactivada(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    servicio.desactivar(u, c.id_categoria)
    with pytest.raises(ErrorNegocio, match="Reactívela"):
        servicio.renombrar(u, c.id_categoria, "Animales")


# =====================================================================
# 3. Desactivar y reactivar (RN-25, CA-14)
# =====================================================================

def test_desactivar_raiz_desactiva_sus_subcategorias(servicio, u):
    """RN-25: una raíz desactivada se lleva a sus subcategorías activas, en una transacción."""
    vivienda = buscar(servicio, u, "Vivienda")
    assert len(vivienda.subcategorias) == 3
    categoria, cuantas = servicio.desactivar(u, vivienda.raiz.id_categoria)
    assert not categoria.activa
    assert cuantas == 3
    todas = servicio.listar_arbol(u, "EGRESO", incluir_inactivas=True)
    rama = next(r for r in todas if r.raiz.id_categoria == vivienda.raiz.id_categoria)
    assert all(not s.activa for s in rama.subcategorias)


def test_desactivar_subcategoria_no_toca_al_padre(servicio, u):
    vivienda = buscar(servicio, u, "Vivienda")
    arriendo = next(s for s in vivienda.subcategorias if s.nombre == "Arriendo")
    _, cuantas = servicio.desactivar(u, arriendo.id_categoria)
    assert cuantas == 0
    assert servicio.obtener(u, vivienda.raiz.id_categoria).activa
    assert [s.nombre for s in buscar(servicio, u, "Vivienda").subcategorias] == ["Hogar y aseo", "Servicios públicos"]


def test_ca14_desactivar_conserva_los_movimientos(servicio, con_tx, u):
    """CA-14: los movimientos de una categoría desactivada se conservan y siguen contando."""
    alimentacion = buscar(servicio, u, "Alimentación").raiz
    cuenta = CuentaServicio(con_tx).crear(u, "Nequi", "OTRA", Decimal("100")).cuenta.id_cuenta
    con_tx.execute(
        "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, monto, fecha) "
        "VALUES (%s, 'EGRESO', %s, %s, 30, %s)",
        (u, cuenta, alimentacion.id_categoria, date(2026, 11, 1)),
    )
    servicio.desactivar(u, alimentacion.id_categoria)

    fila = con_tx.execute("SELECT estado, id_categoria FROM movimiento WHERE id_usuario = %s", (u,)).fetchone()
    assert fila == {"estado": "VIGENTE", "id_categoria": alimentacion.id_categoria}
    assert CuentaServicio(con_tx).obtener(u, cuenta).saldo == Decimal("70.00")


def test_desactivar_dos_veces(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    servicio.desactivar(u, c.id_categoria)
    with pytest.raises(ErrorNegocio, match="ya está desactivada"):
        servicio.desactivar(u, c.id_categoria)


def test_reactivar_raiz_no_reactiva_sus_subcategorias(servicio, u):
    vivienda = buscar(servicio, u, "Vivienda").raiz
    servicio.desactivar(u, vivienda.id_categoria)
    assert servicio.reactivar(u, vivienda.id_categoria).activa
    assert buscar(servicio, u, "Vivienda").subcategorias == []


def test_reactivar_subcategoria_exige_padre_activo(servicio, u):
    vivienda = buscar(servicio, u, "Vivienda")
    arriendo = vivienda.subcategorias[0]
    servicio.desactivar(u, vivienda.raiz.id_categoria)
    with pytest.raises(ErrorNegocio, match="Primero reactive la categoría padre"):
        servicio.reactivar(u, arriendo.id_categoria)
    servicio.reactivar(u, vivienda.raiz.id_categoria)
    assert servicio.reactivar(u, arriendo.id_categoria).activa


def test_reactivar_con_nombre_ocupado(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    servicio.desactivar(u, c.id_categoria)
    servicio.crear(u, "Mascotas", "EGRESO")
    with pytest.raises(ErrorNegocio, match="Cámbiele el nombre"):
        servicio.reactivar(u, c.id_categoria)


def test_reactivar_una_activa(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    with pytest.raises(ErrorNegocio, match="ya está activa"):
        servicio.reactivar(u, c.id_categoria)


# =====================================================================
# 4. Árbol y filtros
# =====================================================================

def test_arbol_de_las_categorias_por_defecto(servicio, u):
    """RN-21, RN-26: 13 raíces; cada subcategoría bajo su raíz."""
    arbol = servicio.listar_arbol(u)
    assert len(arbol) == 13
    assert sum(len(r.subcategorias) for r in arbol) == 21
    assert all(not r.raiz.es_subcategoria() for r in arbol)
    assert all(s.id_padre == r.raiz.id_categoria for r in arbol for s in r.subcategorias)


def test_arbol_filtrado_por_tipo(servicio, u):
    ingresos = servicio.listar_arbol(u, "INGRESO")
    assert {r.raiz.nombre for r in ingresos} == {"Salario", "Trabajo independiente", "Rendimientos", "Otros ingresos"}
    assert all(r.raiz.tipo == "INGRESO" for r in ingresos)


def test_arbol_oculta_desactivadas_salvo_que_se_pidan(servicio, u):
    c = servicio.crear(u, "Mascotas", "EGRESO")
    servicio.desactivar(u, c.id_categoria)
    assert "Mascotas" not in {r.raiz.nombre for r in servicio.listar_arbol(u)}
    assert "Mascotas" in {r.raiz.nombre for r in servicio.listar_arbol(u, incluir_inactivas=True)}


def test_arbol_con_tipo_invalido(servicio, u):
    with pytest.raises(ErrorNegocio, match="INGRESO o EGRESO"):
        servicio.listar_arbol(u, "OTRO")


# =====================================================================
# 5. Categorías de otro usuario (RN-06)
# =====================================================================

@pytest.mark.parametrize("accion", ["obtener", "renombrar", "desactivar", "reactivar"])
def test_categoria_ajena_responde_no_encontrado(servicio, con_tx, u, accion):
    ajena = servicio.crear(nuevo_usuario(con_tx), "Ajena", "EGRESO").id_categoria
    argumentos = ("Robada",) if accion == "renombrar" else ()
    with pytest.raises(NoEncontrado):
        getattr(servicio, accion)(u, ajena, *argumentos)
    with pytest.raises(NoEncontrado):
        getattr(servicio, accion)(u, 999_999_999, *argumentos)


def test_no_se_crea_subcategoria_bajo_un_padre_ajeno(servicio, con_tx, u):
    """RN-04, RN-06: el padre de otro usuario no existe para mí."""
    ajena = servicio.crear(nuevo_usuario(con_tx), "Ajena", "EGRESO").id_categoria
    with pytest.raises(NoEncontrado, match="categoría padre"):
        servicio.crear(u, "Intrusa", id_padre=ajena)


# =====================================================================
# 6. API /api/categorias
# =====================================================================

@pytest.fixture
def api(cliente_api):
    r = cliente_api.post("/api/registro", headers=ENCABEZADOS, json={
        "nombre": "Ana", "correo": f"api.{uuid.uuid4().hex[:10]}@prueba.example", "clave": "clave-segura-123"})
    assert r.status_code == 201
    return cliente_api


def test_api_listar_arbol(api):
    r = api.get("/api/categorias?tipo=INGRESO")
    assert r.status_code == 200
    salario = next(c for c in r.get_json()["categorias"] if c["nombre"] == "Salario")
    assert [s["nombre"] for s in salario["subcategorias"]] == ["Primas y bonificaciones", "Sueldo"]
    assert salario["tipo"] == "INGRESO"


def test_api_crear_renombrar_desactivar_reactivar(api):
    r = api.post("/api/categorias", headers=ENCABEZADOS, json={"nombre": "Mascotas", "tipo": "EGRESO"})
    assert r.status_code == 201
    id_padre = r.get_json()["categoria"]["id_categoria"]

    r = api.post("/api/categorias", headers=ENCABEZADOS, json={"nombre": "Veterinario", "id_padre": id_padre})
    assert r.status_code == 201
    hija = r.get_json()["categoria"]
    assert (hija["tipo"], hija["id_padre"]) == ("EGRESO", id_padre)

    r = api.put(f"/api/categorias/{id_padre}", headers=ENCABEZADOS, json={"nombre": "Animales"})
    assert r.get_json()["categoria"]["nombre"] == "Animales"

    r = api.post(f"/api/categorias/{id_padre}/desactivar", headers=ENCABEZADOS, json={})
    assert r.status_code == 200
    assert r.get_json()["subcategorias_desactivadas"] == 1

    assert api.post(f"/api/categorias/{id_padre}/reactivar", headers=ENCABEZADOS, json={}).status_code == 200
    assert api.get(f"/api/categorias/{id_padre}").get_json()["categoria"]["activa"] is True


@pytest.mark.parametrize("cuerpo", [{"nombre": "Otro", "tipo": "INGRESO"}, {"nombre": "Otro", "id_padre": 1}])
def test_api_renombrar_no_acepta_padre_ni_tipo(api, cuerpo):
    """RN-22: el padre y el tipo no cambian; si llegan, se rechaza en lugar de ignorarlos."""
    id_categoria = api.get("/api/categorias").get_json()["categorias"][0]["id_categoria"]
    r = api.put(f"/api/categorias/{id_categoria}", headers=ENCABEZADOS, json=cuerpo)
    assert r.status_code == 400
    assert "Campos no permitidos" in r.get_json()["error"]


@pytest.mark.parametrize("id_padre", ["5", 1.5, True])
def test_api_id_padre_debe_ser_entero(api, id_padre):
    r = api.post("/api/categorias", headers=ENCABEZADOS, json={"nombre": "X", "id_padre": id_padre})
    assert r.status_code == 400
    assert "número entero" in r.get_json()["error"]


def test_api_tercer_nivel_rechazado(api):
    salario = next(c for c in api.get("/api/categorias?tipo=INGRESO").get_json()["categorias"]
                   if c["nombre"] == "Salario")
    sueldo = salario["subcategorias"][0]["id_categoria"]
    r = api.post("/api/categorias", headers=ENCABEZADOS, json={"nombre": "Horas extra", "id_padre": sueldo})
    assert r.status_code == 400
    assert "dos niveles" in r.get_json()["error"]


def test_api_categoria_ajena_responde_404(api, con_tx):
    ajena = CategoriaServicio(con_tx).crear(nuevo_usuario(con_tx), "Ajena", "EGRESO").id_categoria
    assert api.get(f"/api/categorias/{ajena}").status_code == 404
    r = api.post(f"/api/categorias/{ajena}/desactivar", headers=ENCABEZADOS, json={})
    assert r.status_code == 404
    assert r.get_json() == {"error": "No se encontró la categoría."}


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/api/categorias"),
    ("post", "/api/categorias"),
    ("get", "/api/categorias/1"),
    ("put", "/api/categorias/1"),
    ("post", "/api/categorias/1/desactivar"),
    ("post", "/api/categorias/1/reactivar"),
])
def test_api_sin_sesion_responde_401(cliente_api, metodo, ruta):
    r = getattr(cliente_api, metodo)(ruta, headers=ENCABEZADOS, json={})
    assert r.status_code == 401
