"""Pruebas de la autenticación (Tarea 7, RF-01).

Qué verifican
    * Servicio: registro con correo normalizado y contraseña con hash (RN-01,
      RN-02), copia de las categorías por defecto en la misma transacción
      (RN-26), validaciones e inicio de sesión.
    * Restablecer una contraseña olvidada (scripts/cambiar_clave.py): se guarda
      solo el hash de la nueva, con la misma regla de longitud que el registro.
    * API: el flujo registro -> ver sesión -> cerrar -> iniciar sesión, con
      la cookie real de Flask, y que un usuario nuevo inicia sesión y ya tiene
      sus categorías (criterio de terminado de la Tarea 7).

Cómo dejan la base como estaba
    El servicio confirma su transacción (COMMIT) al registrar. Para que eso no
    deje usuarios en la base de pruebas, aquí se usa UNA conexión que ya tiene
    una transacción abierta: dentro de ella, con.transaction() del servicio se
    convierte en un SAVEPOINT, y al final de la prueba se deshace todo con
    ROLLBACK. Se hace con BaseDatosDePrueba y las conexiones con_tx y
    cliente_api, definidas en conftest.py.
"""

import uuid

import pytest
from werkzeug.security import check_password_hash

from app.entidades.categoria import TipoCategoria
from app.errores import ErrorNegocio, NoAutenticado, NoEncontrado
from app.repositorios.categorias import CategoriaRepositorio
from app.servicios.autenticacion import MENSAJE_CREDENCIALES, AutenticacionServicio
from app.servicios.categorias_por_defecto import CATEGORIAS_POR_DEFECTO

CLAVE = "clave-segura-123"
ENCABEZADOS = {"X-Requested-With": "financia"}

TOTAL_CATEGORIAS = sum(1 + len(subs) for lista in CATEGORIAS_POR_DEFECTO.values() for _, subs in lista)
TOTAL_RAICES = sum(len(lista) for lista in CATEGORIAS_POR_DEFECTO.values())


@pytest.fixture
def servicio(con_tx):
    return AutenticacionServicio(con_tx)


def correo_nuevo() -> str:
    return f"ana.{uuid.uuid4().hex[:10]}@prueba.example"


def existe_usuario(con_tx, correo) -> bool:
    return con_tx.execute("SELECT 1 FROM usuario WHERE correo = %s", (correo,)).fetchone() is not None


# =====================================================================
# 1. Servicio: registro
# =====================================================================

def test_registro_normaliza_correo_y_guarda_hash(servicio):
    """RN-01 y RN-02: correo en minúsculas y sin espacios; la contraseña nunca en texto plano."""
    correo = correo_nuevo()
    usuario = servicio.registrar("  Ana  ", f"  {correo.upper()} ", CLAVE)
    assert usuario.nombre == "Ana"
    assert usuario.correo == correo
    assert usuario.clave_hash != CLAVE
    assert check_password_hash(usuario.clave_hash, CLAVE)


def test_registro_copia_las_categorias_por_defecto(servicio, con_tx):
    """RN-26: el usuario nuevo recibe la lista completa, con subcategorías del mismo tipo que su padre."""
    usuario = servicio.registrar("Ana", correo_nuevo(), CLAVE)
    categorias = CategoriaRepositorio(con_tx).listar(usuario.id_usuario)

    assert len(categorias) == TOTAL_CATEGORIAS == 34
    assert sum(1 for c in categorias if not c.es_subcategoria()) == TOTAL_RAICES == 13
    assert all(c.activa and c.id_usuario == usuario.id_usuario for c in categorias)

    por_id = {c.id_categoria: c for c in categorias}
    for c in categorias:
        if c.es_subcategoria():
            assert por_id[c.id_padre].tipo == c.tipo
            assert not por_id[c.id_padre].es_subcategoria()   # dos niveles como máximo (RN-21)


def test_registro_incluye_impuestos_y_comisiones(servicio, con_tx):
    """RN-26: 'Impuestos y comisiones' (EGRESO) existe siempre, con 4×1.000 y Comisiones bancarias."""
    usuario = servicio.registrar("Ana", correo_nuevo(), CLAVE)
    categorias = CategoriaRepositorio(con_tx).listar(usuario.id_usuario)
    impuestos = next(c for c in categorias if c.nombre == "Impuestos y comisiones")
    assert impuestos.tipo == TipoCategoria.EGRESO
    hijas = {c.nombre for c in categorias if c.id_padre == impuestos.id_categoria}
    assert hijas == {"4×1.000", "Comisiones bancarias"}


def test_registro_es_una_sola_transaccion(servicio, con_tx, monkeypatch):
    """RN-26: si falla la copia de una categoría, tampoco queda el usuario."""
    original = CategoriaRepositorio.insertar
    llamadas = {"n": 0}

    def insertar_que_falla(self, *args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 5:
            raise RuntimeError("falla simulada en la quinta categoría")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CategoriaRepositorio, "insertar", insertar_que_falla)
    correo = correo_nuevo()
    with pytest.raises(RuntimeError):
        servicio.registrar("Ana", correo, CLAVE)
    # Las 4 categorías que sí alcanzaron a insertarse se deshicieron junto con el usuario:
    # sin la transacción, el usuario quedaría guardado con solo 4 categorías.
    assert not existe_usuario(con_tx, correo)


def test_registro_rechaza_correo_repetido_sin_importar_mayusculas(servicio):
    """RN-01: el correo no se repite."""
    correo = correo_nuevo()
    servicio.registrar("Ana", correo, CLAVE)
    with pytest.raises(ErrorNegocio, match="Ya existe un usuario con ese correo"):
        servicio.registrar("Otra Ana", correo.upper(), CLAVE)


@pytest.mark.parametrize("nombre, correo, clave, mensaje", [
    ("   ", "ana@prueba.example", CLAVE, "El nombre es obligatorio"),
    ("Ana", "ana.prueba.example", CLAVE, "El correo no es válido"),
    ("Ana", "@prueba.example", CLAVE, "El correo no es válido"),
    ("Ana", "ana@prueba", CLAVE, "El correo no es válido"),
    ("Ana", "ana @prueba.example", CLAVE, "El correo no es válido"),
    ("Ana", "ana@prueba.example", "1234567", "al menos 8 caracteres"),
])
def test_registro_valida_los_datos(servicio, con_tx, nombre, correo, clave, mensaje):
    """RF-01: datos incompletos o mal escritos se rechazan con un mensaje claro y no se guarda nada."""
    with pytest.raises(ErrorNegocio, match=mensaje):
        servicio.registrar(nombre, correo, clave)
    assert not existe_usuario(con_tx, correo.strip().lower())


# =====================================================================
# 2. Servicio: inicio de sesión
# =====================================================================

def test_inicio_de_sesion_correcto_sin_importar_mayusculas_del_correo(servicio):
    correo = correo_nuevo()
    registrado = servicio.registrar("Ana", correo, CLAVE)
    assert servicio.iniciar_sesion(f" {correo.upper()} ", CLAVE) == registrado


def test_inicio_de_sesion_con_clave_incorrecta(servicio):
    correo = correo_nuevo()
    servicio.registrar("Ana", correo, CLAVE)
    with pytest.raises(NoAutenticado, match=MENSAJE_CREDENCIALES):
        servicio.iniciar_sesion(correo, "otra-clave-123")


def test_inicio_de_sesion_con_correo_inexistente_da_el_mismo_mensaje(servicio):
    """No revela si el correo está registrado."""
    with pytest.raises(NoAutenticado, match=MENSAJE_CREDENCIALES):
        servicio.iniciar_sesion(correo_nuevo(), CLAVE)


def test_usuario_desactivado_no_inicia_sesion(servicio, con_tx):
    correo = correo_nuevo()
    usuario = servicio.registrar("Ana", correo, CLAVE)
    con_tx.execute("UPDATE usuario SET activo = false WHERE id_usuario = %s", (usuario.id_usuario,))
    with pytest.raises(NoAutenticado, match=MENSAJE_CREDENCIALES):
        servicio.iniciar_sesion(correo, CLAVE)


# =====================================================================
# Restablecer una contraseña olvidada (herramienta de administración)
# =====================================================================

NUEVA = "nueva-clave-456"


def test_restablecer_clave_cambia_la_contrasena(servicio, con_tx):
    """RN-02: entra con la nueva, ya no con la vieja, y la base guarda solo su hash."""
    correo = correo_nuevo()
    usuario = servicio.registrar("Ana", correo, CLAVE)
    assert servicio.restablecer_clave(f" {correo.upper()} ", NUEVA).id_usuario == usuario.id_usuario
    assert servicio.iniciar_sesion(correo, NUEVA).id_usuario == usuario.id_usuario
    with pytest.raises(NoAutenticado):
        servicio.iniciar_sesion(correo, CLAVE)
    guardado = con_tx.execute("SELECT clave_hash FROM usuario WHERE id_usuario = %s",
                              (usuario.id_usuario,)).fetchone()["clave_hash"]
    assert NUEVA not in guardado and check_password_hash(guardado, NUEVA)


def test_restablecer_clave_exige_8_caracteres_y_no_cambia_nada(servicio):
    correo = correo_nuevo()
    servicio.registrar("Ana", correo, CLAVE)
    with pytest.raises(ErrorNegocio, match="al menos 8 caracteres"):
        servicio.restablecer_clave(correo, "corta")
    assert servicio.iniciar_sesion(correo, CLAVE)   # la vieja sigue sirviendo


def test_restablecer_clave_de_un_correo_inexistente(servicio):
    with pytest.raises(NoEncontrado, match="No hay ningún usuario con ese correo"):
        servicio.restablecer_clave(correo_nuevo(), NUEVA)


def test_restablecer_clave_solo_cambia_ese_usuario(servicio):
    ana, beto = correo_nuevo(), correo_nuevo()
    servicio.registrar("Ana", ana, CLAVE)
    servicio.registrar("Beto", beto, CLAVE)
    servicio.restablecer_clave(ana, NUEVA)
    assert servicio.iniciar_sesion(beto, CLAVE)


def test_listar_usuarios_muestra_nombre_y_correo(servicio):
    correo = correo_nuevo()
    servicio.registrar("Ana Lista", correo, CLAVE)
    usuarios = {u.correo: u for u in servicio.listar_usuarios()}
    assert usuarios[correo].nombre == "Ana Lista"
    assert "clave_hash" not in repr(usuarios[correo])   # el hash no aparece si se imprime


# =====================================================================
# 3. API: flujo completo con la cookie de sesión
# =====================================================================

def test_usuario_nuevo_inicia_sesion_y_ya_tiene_sus_categorias(cliente_api, con_tx):
    """Criterio de terminado de la Tarea 7 (RF-01, RN-26)."""
    correo = correo_nuevo()

    r = cliente_api.post("/api/registro", json={"nombre": "Ana", "correo": correo, "clave": CLAVE},
                     headers=ENCABEZADOS)
    assert r.status_code == 201
    id_usuario = r.get_json()["usuario"]["id_usuario"]

    r = cliente_api.delete("/api/sesion", json={}, headers=ENCABEZADOS)
    assert r.status_code == 200
    assert cliente_api.get("/api/sesion").status_code == 401

    r = cliente_api.post("/api/sesion", json={"correo": correo, "clave": CLAVE}, headers=ENCABEZADOS)
    assert r.status_code == 200
    assert r.get_json() == {"usuario": {"id_usuario": id_usuario, "nombre": "Ana", "correo": correo}}

    r = cliente_api.get("/api/sesion")
    assert r.status_code == 200
    assert r.get_json()["usuario"]["id_usuario"] == id_usuario

    assert len(CategoriaRepositorio(con_tx).listar(id_usuario)) == TOTAL_CATEGORIAS


def test_registro_deja_la_sesion_iniciada(cliente_api):
    cliente_api.post("/api/registro", json={"nombre": "Ana", "correo": correo_nuevo(), "clave": CLAVE},
                 headers=ENCABEZADOS)
    assert cliente_api.get("/api/sesion").status_code == 200


def test_la_respuesta_nunca_incluye_el_hash(cliente_api):
    """RN-02: el hash de la contraseña no sale del servidor."""
    r = cliente_api.post("/api/registro", json={"nombre": "Ana", "correo": correo_nuevo(), "clave": CLAVE},
                     headers=ENCABEZADOS)
    assert "clave_hash" not in r.get_data(as_text=True)
    assert CLAVE not in r.get_data(as_text=True)


def test_cookie_de_sesion_httponly_y_samesite_lax(cliente_api):
    """ARQUITECTURA 6: JavaScript no puede leer la cookie y otros sitios no la envían en un POST."""
    r = cliente_api.post("/api/registro", json={"nombre": "Ana", "correo": correo_nuevo(), "clave": CLAVE},
                     headers=ENCABEZADOS)
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_sin_sesion_responde_401_en_json(cliente_api):
    r = cliente_api.get("/api/sesion")
    assert r.status_code == 401
    assert r.get_json() == {"error": "Debe iniciar sesión."}


def test_cookie_alterada_no_da_sesion(cliente_api):
    """La cookie está firmada con SECRET_KEY: una cookie inventada no sirve."""
    cliente_api.set_cookie("session", "eyJpZF91c3VhcmlvIjoxfQ.inventada.firma")
    assert cliente_api.get("/api/sesion").status_code == 401


def test_sesion_de_usuario_desactivado_deja_de_valer(cliente_api, con_tx):
    r = cliente_api.post("/api/registro", json={"nombre": "Ana", "correo": correo_nuevo(), "clave": CLAVE},
                     headers=ENCABEZADOS)
    id_usuario = r.get_json()["usuario"]["id_usuario"]
    con_tx.execute("UPDATE usuario SET activo = false WHERE id_usuario = %s", (id_usuario,))
    assert cliente_api.get("/api/sesion").status_code == 401


def test_inicio_de_sesion_fallido_responde_401(cliente_api):
    r = cliente_api.post("/api/sesion", json={"correo": correo_nuevo(), "clave": CLAVE}, headers=ENCABEZADOS)
    assert r.status_code == 401
    assert r.get_json() == {"error": MENSAJE_CREDENCIALES}


def test_registro_con_correo_repetido_responde_400(cliente_api):
    correo = correo_nuevo()
    datos = {"nombre": "Ana", "correo": correo, "clave": CLAVE}
    cliente_api.post("/api/registro", json=datos, headers=ENCABEZADOS)
    r = cliente_api.post("/api/registro", json=datos, headers=ENCABEZADOS)
    assert r.status_code == 400
    assert r.get_json() == {"error": "Ya existe un usuario con ese correo."}


@pytest.mark.parametrize("cuerpo", [
    {"nombre": "Ana", "correo": "ana@prueba.example"},                 # falta la clave
    {"nombre": "Ana", "correo": "ana@prueba.example", "clave": 12345678},  # la clave no es texto
    ["no", "es", "un", "objeto"],
])
def test_registro_con_cuerpo_mal_formado_responde_400(cliente_api, cuerpo):
    r = cliente_api.post("/api/registro", json=cuerpo, headers=ENCABEZADOS)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_registro_sin_encabezado_csrf_es_rechazado(cliente_api, con_tx):
    """ARQUITECTURA 6: sin X-Requested-With: financia no se crea nada."""
    correo = correo_nuevo()
    r = cliente_api.post("/api/registro", json={"nombre": "Ana", "correo": correo, "clave": CLAVE})
    assert r.status_code == 403
    assert not existe_usuario(con_tx, correo)
