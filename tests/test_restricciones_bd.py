"""Pruebas de las restricciones de la base de datos (Tarea 5).

ESTADO: escrito y revisado a mano. TODAVÍA NO SE HA EJECUTADO.

Qué verifican
    Que la base, POR SÍ SOLA, rechaza lo que el modelo dice que debe rechazar
    y acepta lo que debe aceptar. No prueban la aplicación (aún no existe).

Cómo están hechas
    * Cada rechazo comprueba DOS cosas: el tipo de error y el NOMBRE de la
      restricción que lo produjo. Así se evita el falso positivo de "lo rechazó,
      pero por otra razón" (por ejemplo, porque faltaba otro dato).
    * Por eso cada caso parte de una fila VÁLIDA y cambia UNA sola cosa.
    * Hay pruebas "de control" que insertan filas válidas: si esas fallan, las
      demás no significan nada.
    * Hay pruebas marcadas LÍMITE CONOCIDO: documentan reglas que la base NO
      garantiza y que debe cumplir la capa de servicios.

Cada prueba cita la regla (RN-xx), el criterio (CA-xx) o la decisión (D-xx)
que verifica. Ver docs/REGLAS_NEGOCIO.md, docs/REQUISITOS.md y
docs/DECISIONES_ARQUITECTURA.md.

Ejecutar (cuando el entorno esté listo):
    pytest tests/test_restricciones_bd.py -v
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from psycopg import errors, sql

FECHA = date(2026, 11, 1)


# =====================================================================
# Utilidades
# =====================================================================

def _insert(tabla, columnas):
    """Arma un INSERT parametrizado. Devuelve (consulta, valores)."""
    nombres = list(columnas)
    consulta = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(tabla),
        sql.SQL(", ").join(sql.Identifier(n) for n in nombres),
        sql.SQL(", ").join(sql.Placeholder() for _ in nombres),
    )
    return consulta, [columnas[n] for n in nombres]


def insertar(con, tabla, **columnas):
    """Inserta una fila y devuelve su identificador (la primera columna)."""
    consulta, valores = _insert(tabla, columnas)
    return con.execute(consulta, valores).fetchone()[0]


def rechaza(con, error, restriccion, consulta, valores=None):
    """Comprueba que la base rechaza la sentencia con ese error y esa restricción.

    'restriccion' puede ser un nombre o una tupla de nombres aceptables.
    La sentencia corre dentro de un punto de guardado (con.transaction()), de
    modo que el error no daña la transacción de la prueba.
    """
    with pytest.raises(error) as info:
        with con.transaction():
            con.execute(consulta, valores)
    aceptadas = (restriccion,) if isinstance(restriccion, str) else restriccion
    assert info.value.diag.constraint_name in aceptadas, (
        f"Se rechazó, pero por la restricción {info.value.diag.constraint_name!r} "
        f"y se esperaba {aceptadas!r}."
    )


def rechaza_insertar(con, error, restriccion, tabla, **columnas):
    consulta, valores = _insert(tabla, columnas)
    rechaza(con, error, restriccion, consulta, valores)


def nuevo_usuario(con, nombre):
    correo = f"{nombre.lower()}.{uuid.uuid4().hex[:10]}@prueba.example"
    return insertar(con, "usuario", nombre=nombre, correo=correo, clave_hash="hash-de-prueba")


@pytest.fixture
def m(con):
    """Mundo mínimo: dos usuarios, con cuentas y categorías propias."""
    u1 = nuevo_usuario(con, "Uno")
    u2 = nuevo_usuario(con, "Dos")
    return SimpleNamespace(
        u1=u1,
        u2=u2,
        nequi=insertar(con, "cuenta", id_usuario=u1, nombre="Nequi", tipo="BILLETERA_DIGITAL", saldo_inicial=Decimal("500000")),
        nubank=insertar(con, "cuenta", id_usuario=u1, nombre="Nubank", tipo="AHORROS"),
        efectivo=insertar(con, "cuenta", id_usuario=u1, nombre="Efectivo", tipo="EFECTIVO"),
        cuenta_u2=insertar(con, "cuenta", id_usuario=u2, nombre="Nequi", tipo="BILLETERA_DIGITAL"),
        cat_ing=insertar(con, "categoria", id_usuario=u1, nombre="Salario", tipo="INGRESO"),
        cat_egr=insertar(con, "categoria", id_usuario=u1, nombre="Comida", tipo="EGRESO"),
        cat_cargos=insertar(con, "categoria", id_usuario=u1, nombre="Impuestos y comisiones", tipo="EGRESO"),
        cat_ing_u2=insertar(con, "categoria", id_usuario=u2, nombre="Salario", tipo="INGRESO"),
        cat_egr_u2=insertar(con, "categoria", id_usuario=u2, nombre="Comida", tipo="EGRESO"),
    )


def fila_mov(m, tipo, **cambios):
    """Devuelve las columnas de un movimiento VÁLIDO de ese tipo, con los cambios pedidos."""
    base = dict(id_usuario=m.u1, tipo=tipo, id_cuenta=m.nequi, monto=Decimal("1000"), fecha=FECHA)
    if tipo == "INGRESO":
        base["id_categoria"] = m.cat_ing
    elif tipo == "EGRESO":
        base["id_categoria"] = m.cat_egr
    elif tipo == "TRANSFERENCIA":
        base["id_cuenta_destino"] = m.nubank
    elif tipo in ("AJUSTE_AUMENTO", "AJUSTE_DISMINUCION"):
        base["descripcion"] = "Compras no registradas"
    base.update(cambios)
    return base


def nueva_transferencia(con, m, monto="200000"):
    return insertar(con, "movimiento", **fila_mov(m, "TRANSFERENCIA", monto=Decimal(monto)))


# =====================================================================
# 0. Estructura general
# =====================================================================

def test_existen_exactamente_las_seis_tablas(con):
    """D-01: seis tablas y ninguna para funcionalidades futuras."""
    filas = con.execute(
        """
        SELECT table_name FROM information_schema.tables
         WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'
        """
    ).fetchall()
    tablas = {f[0] for f in filas} - {"migracion_aplicada"}  # tabla de control del script de migraciones
    assert tablas == {"usuario", "cuenta", "categoria", "movimiento", "bolsillo", "bolsillo_valor"}


def test_no_hay_triggers(con):
    """D-14: cero triggers en la versión 1."""
    cantidad = con.execute(
        """
        SELECT count(*)
          FROM pg_trigger t
          JOIN pg_class c     ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE NOT t.tgisinternal AND n.nspname = current_schema()
        """
    ).fetchone()[0]
    assert cantidad == 0


def test_ninguna_fk_borra_ni_actualiza_en_cascada(con):
    """RN-70: ninguna clave foránea tiene acciones en cascada ('a' = NO ACTION)."""
    filas = con.execute(
        """
        SELECT k.conname
          FROM pg_constraint k
          JOIN pg_namespace n ON n.oid = k.connamespace
         WHERE k.contype = 'f' AND n.nspname = current_schema()
           AND (k.confdeltype <> 'a' OR k.confupdtype <> 'a')
        """
    ).fetchall()
    assert filas == []


def test_bolsillos_no_se_relacionan_con_cuentas_ni_movimientos(con):
    """D-10, RN-39, RN-40: no existe FK entre bolsillos y cuentas o movimientos, en ningún sentido."""
    filas = con.execute(
        """
        SELECT k.conname
          FROM pg_constraint k
         WHERE k.contype = 'f'
           AND (   (k.conrelid  IN ('bolsillo'::regclass, 'bolsillo_valor'::regclass)
                    AND k.confrelid IN ('cuenta'::regclass, 'movimiento'::regclass))
                OR (k.conrelid  IN ('cuenta'::regclass, 'movimiento'::regclass)
                    AND k.confrelid IN ('bolsillo'::regclass, 'bolsillo_valor'::regclass)))
        """
    ).fetchall()
    assert filas == []


def test_todas_las_tablas_y_columnas_tienen_comentario(con):
    """Lista de control de la Tarea 3: COMMENT ON TABLE y COMMENT ON COLUMN en todo."""
    sin_comentario = con.execute(
        """
        SELECT c.relname, a.attname
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
         WHERE n.nspname = current_schema() AND c.relkind = 'r'
           AND c.relname <> 'migracion_aplicada'
           AND (col_description(c.oid, a.attnum) IS NULL OR obj_description(c.oid, 'pg_class') IS NULL)
        """
    ).fetchall()
    assert sin_comentario == []


# =====================================================================
# 1. Usuario
# =====================================================================

def test_correo_duplicado(con):
    """RN-01."""
    insertar(con, "usuario", nombre="Ana", correo="ana.unica@prueba.example", clave_hash="h")
    rechaza_insertar(con, errors.UniqueViolation, "uq_usuario_correo", "usuario",
                     nombre="Otra Ana", correo="ana.unica@prueba.example", clave_hash="h")


@pytest.mark.parametrize("correo", ["Ana.Mayus@prueba.example", " espacio@prueba.example", "espacio@prueba.example ", ""])
def test_correo_debe_llegar_normalizado(con, correo):
    """RN-01: sin este CHECK, 'Ana@x' y 'ana@x' serían dos usuarios distintos para UNIQUE."""
    rechaza_insertar(con, errors.CheckViolation, "ck_usuario_correo", "usuario",
                     nombre="Ana", correo=correo, clave_hash="h")


@pytest.mark.parametrize("nombre", ["", "   ", " Ana", "Ana "])
def test_nombre_de_usuario_vacio_o_con_espacios_extremos(con, nombre):
    """MODELO_DATOS 4.1: nombre no vacío y sin espacios al inicio ni al final."""
    rechaza_insertar(con, errors.CheckViolation, "ck_usuario_nombre", "usuario",
                     nombre=nombre, correo=f"{uuid.uuid4().hex}@prueba.example", clave_hash="h")


# =====================================================================
# 2. Cuenta
# =====================================================================

def test_cuenta_valida_con_valores_por_defecto(con, m):
    """Control. RN-10: tipo OTRA, saldo inicial 0 y activa si no se indican."""
    id_cuenta = insertar(con, "cuenta", id_usuario=m.u1, nombre="Alcancía")
    fila = con.execute("SELECT tipo, saldo_inicial, activa FROM cuenta WHERE id_cuenta = %s", [id_cuenta]).fetchone()
    assert fila == ("OTRA", Decimal("0.00"), True)


def test_saldo_inicial_negativo(con, m):
    """RN-10."""
    rechaza_insertar(con, errors.CheckViolation, "ck_cuenta_saldo_inicial", "cuenta",
                     id_usuario=m.u1, nombre="Deuda", saldo_inicial=Decimal("-0.01"))


@pytest.mark.parametrize("tipo", ["TARJETA_CREDITO", "ahorros", ""])
def test_tipo_de_cuenta_invalido(con, m, tipo):
    """D-16. Incluye TARJETA_CREDITO (aplazada) y el valor correcto en minúsculas."""
    rechaza_insertar(con, errors.CheckViolation, "ck_cuenta_tipo", "cuenta",
                     id_usuario=m.u1, nombre="Rara", tipo=tipo)


def test_cuenta_de_usuario_inexistente(con):
    """RN-03."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_cuenta_usuario", "cuenta",
                     id_usuario=-1, nombre="Huérfana")


@pytest.mark.parametrize("nombre", ["Nequi", "NEQUI", "nequi"])
def test_nombre_de_cuenta_repetido_entre_activas(con, m, nombre):
    """Índice único parcial: no distingue mayúsculas."""
    rechaza_insertar(con, errors.UniqueViolation, "uq_cuenta_nombre_activa", "cuenta",
                     id_usuario=m.u1, nombre=nombre)


def test_mismo_nombre_de_cuenta_en_usuarios_distintos(con, m):
    """Control: el fixture ya creó 'Nequi' para U1 y para U2. La unicidad es por usuario."""
    cantidad = con.execute(
        "SELECT count(*) FROM cuenta WHERE id_usuario IN (%s, %s) AND nombre = 'Nequi'", [m.u1, m.u2]
    ).fetchone()[0]
    assert cantidad == 2


def test_cuenta_archivada_libera_el_nombre_y_no_se_reactiva_si_choca(con, m):
    """Caso límite del índice parcial: solo vigila las cuentas activas."""
    con.execute("UPDATE cuenta SET activa = false WHERE id_cuenta = %s", [m.nequi])
    insertar(con, "cuenta", id_usuario=m.u1, nombre="Nequi")  # ahora sí se permite
    rechaza(con, errors.UniqueViolation, "uq_cuenta_nombre_activa",
            "UPDATE cuenta SET activa = true WHERE id_cuenta = %s", [m.nequi])


def test_dos_cuentas_archivadas_pueden_llamarse_igual(con, m):
    """Caso límite: entre archivadas no hay restricción de nombre."""
    con.execute("UPDATE cuenta SET activa = false WHERE id_cuenta = %s", [m.nequi])
    otra = insertar(con, "cuenta", id_usuario=m.u1, nombre="Nequi")
    con.execute("UPDATE cuenta SET activa = false WHERE id_cuenta = %s", [otra])


@pytest.mark.parametrize("nombre", ["", "  ", " Ahorros", "Ahorros "])
def test_nombre_de_cuenta_vacio_o_con_espacios_extremos(con, m, nombre):
    """Sin esta regla, 'Nequi' y 'Nequi ' pasarían como nombres distintos."""
    rechaza_insertar(con, errors.CheckViolation, "ck_cuenta_nombre", "cuenta",
                     id_usuario=m.u1, nombre=nombre)


def test_no_se_puede_borrar_una_cuenta_con_movimientos(con, m):
    """RN-70: sin ON DELETE CASCADE, la historia impide el borrado físico.
    (Las pruebas usan el rol dueño de las tablas, que sí puede intentar un DELETE;
    el rol de la aplicación ni siquiera tendrá ese permiso, D-15.)"""
    insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_cuenta",
            "DELETE FROM cuenta WHERE id_cuenta = %s", [m.nequi])


def test_no_se_puede_cambiar_el_dueno_de_una_cuenta_con_movimientos(con, m):
    """RN-03: las FK compuestas también impiden 'regalar' una cuenta con historia a otro usuario.
    Se usa 'Efectivo' porque U2 no tiene una cuenta con ese nombre: así el único
    obstáculo es la clave foránea y no el índice de nombres únicos."""
    insertar(con, "movimiento", **fila_mov(m, "EGRESO", id_cuenta=m.efectivo))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_cuenta",
            "UPDATE cuenta SET id_usuario = %s WHERE id_cuenta = %s", [m.u2, m.efectivo])


# =====================================================================
# 3. Categoría
# =====================================================================

def test_subcategoria_valida(con, m):
    """Control. RN-23."""
    assert insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")


@pytest.mark.parametrize("nombre", ["", "  ", " Mercado", "Mercado "])
def test_nombre_de_categoria_vacio_o_con_espacios_extremos(con, m, nombre):
    """MODELO_DATOS 4.3. Sin esta regla, 'Mercado' y 'Mercado ' pasarían como hermanas distintas (RN-24)."""
    rechaza_insertar(con, errors.CheckViolation, "ck_categoria_nombre", "categoria",
                     id_usuario=m.u1, nombre=nombre, tipo="EGRESO")


def test_categoria_y_bolsillo_de_usuario_inexistente(con):
    """RN-03: todo registro pertenece a un usuario que existe."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_categoria_usuario", "categoria",
                     id_usuario=-1, nombre="Huérfana", tipo="EGRESO")
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_bolsillo_usuario", "bolsillo",
                     id_usuario=-1, nombre="Huérfano")


@pytest.mark.parametrize("tipo", ["GASTO", "egreso", "TRANSFERENCIA"])
def test_tipo_de_categoria_invalido(con, m, tipo):
    """RN-20."""
    rechaza_insertar(con, errors.CheckViolation, "ck_categoria_tipo", "categoria",
                     id_usuario=m.u1, nombre="Rara", tipo=tipo)


def test_padre_de_otro_usuario(con, m):
    """RN-23, RN-04, CA-06."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_categoria_padre", "categoria",
                     id_usuario=m.u1, id_padre=m.cat_egr_u2, nombre="Mercado", tipo="EGRESO")


def test_padre_de_otro_tipo(con, m):
    """RN-23: una subcategoría de EGRESO no puede colgar de una categoría de INGRESO."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_categoria_padre", "categoria",
                     id_usuario=m.u1, id_padre=m.cat_ing, nombre="Mercado", tipo="EGRESO")


def test_padre_inexistente(con, m):
    """RN-23: el padre debe existir."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_categoria_padre", "categoria",
                     id_usuario=m.u1, id_padre=-1, nombre="Mercado", tipo="EGRESO")


def test_categoria_no_puede_ser_su_propio_padre(con, m):
    """Caso límite: la FK sola lo aceptaría (mismo usuario y tipo); lo impide el CHECK."""
    rechaza(con, errors.CheckViolation, "ck_categoria_padre_distinto",
            "UPDATE categoria SET id_padre = id_categoria WHERE id_categoria = %s", [m.cat_egr])


def test_no_se_puede_cambiar_el_tipo_de_un_padre_con_hijas(con, m):
    """RN-22 y RN-23: las hijas dejarían de tener un padre de su mismo tipo."""
    insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")
    rechaza(con, errors.ForeignKeyViolation, "fk_categoria_padre",
            "UPDATE categoria SET tipo = 'INGRESO' WHERE id_categoria = %s", [m.cat_egr])


def test_no_se_puede_cambiar_el_tipo_de_una_categoria_con_movimientos(con, m):
    """RN-22 y RN-31: sus movimientos quedarían con una categoría de otro tipo."""
    insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_categoria",
            "UPDATE categoria SET tipo = 'INGRESO' WHERE id_categoria = %s", [m.cat_egr])


@pytest.mark.parametrize("nombre", ["Mercado", "MERCADO", "mercado"])
def test_nombre_repetido_entre_hermanas(con, m, nombre):
    """RN-24."""
    insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")
    rechaza_insertar(con, errors.UniqueViolation, "uq_categoria_hermanas_activas", "categoria",
                     id_usuario=m.u1, id_padre=m.cat_egr, nombre=nombre, tipo="EGRESO")


def test_nombre_repetido_entre_raices_del_mismo_tipo(con, m):
    """RN-24. Caso límite: las raíces tienen id_padre NULL y UNIQUE trata dos NULL como
    distintos. Esta prueba falla si al índice le falta COALESCE(id_padre, 0)."""
    rechaza_insertar(con, errors.UniqueViolation, "uq_categoria_hermanas_activas", "categoria",
                     id_usuario=m.u1, nombre="COMIDA", tipo="EGRESO")


def test_mismo_nombre_permitido_donde_no_son_hermanas(con, m):
    """RN-24: lo que el índice NO debe impedir."""
    # Raíz con el mismo nombre pero de otro tipo.
    insertar(con, "categoria", id_usuario=m.u1, nombre="Comida", tipo="INGRESO")
    # Hija con el mismo nombre que su padre.
    insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Comida", tipo="EGRESO")
    # El mismo nombre bajo dos padres distintos.
    insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Varios", tipo="EGRESO")
    insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_cargos, nombre="Varios", tipo="EGRESO")
    # El mismo nombre en otro usuario (el fixture ya tiene 'Comida' de U2).


def test_hermana_desactivada_libera_el_nombre(con, m):
    """RN-22, RN-24, RN-25: para reorganizar se crea otra y se desactiva la anterior."""
    vieja = insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")
    con.execute("UPDATE categoria SET activa = false WHERE id_categoria = %s", [vieja])
    insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")
    rechaza(con, errors.UniqueViolation, "uq_categoria_hermanas_activas",
            "UPDATE categoria SET activa = true WHERE id_categoria = %s", [vieja])


def test_limite_conocido_la_base_acepta_un_tercer_nivel(con, m):
    """LÍMITE CONOCIDO (RN-21): la base NO limita la profundidad a dos niveles.
    Lo debe validar el servicio de categorías. Si algún día se agrega esa
    restricción a la base, esta prueba debe invertirse."""
    hija = insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")
    assert insertar(con, "categoria", id_usuario=m.u1, id_padre=hija, nombre="Frutas", tipo="EGRESO")


# =====================================================================
# 4. Movimiento: filas válidas (control)
# =====================================================================

@pytest.mark.parametrize("tipo", ["INGRESO", "EGRESO", "TRANSFERENCIA", "AJUSTE_AUMENTO", "AJUSTE_DISMINUCION"])
def test_movimiento_valido_de_cada_tipo(con, m, tipo):
    """Control: la fila base de cada tipo es válida y nace VIGENTE."""
    id_mov = insertar(con, "movimiento", **fila_mov(m, tipo))
    estado = con.execute("SELECT estado FROM movimiento WHERE id_movimiento = %s", [id_mov]).fetchone()[0]
    assert estado == "VIGENTE"


def test_ingreso_y_egreso_con_subcategoria_y_sin_descripcion(con, m):
    """RN-30, RN-32: se puede usar una subcategoría; la descripción es opcional."""
    sub = insertar(con, "categoria", id_usuario=m.u1, id_padre=m.cat_egr, nombre="Mercado", tipo="EGRESO")
    assert insertar(con, "movimiento", **fila_mov(m, "EGRESO", id_categoria=sub, descripcion=None))


def test_anular_y_reactivar(con, m):
    """RN-70, RN-71: anular es cambiar el estado; la fila se conserva."""
    id_mov = insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    con.execute("UPDATE movimiento SET estado = 'ANULADO' WHERE id_movimiento = %s", [id_mov])
    con.execute("UPDATE movimiento SET estado = 'VIGENTE' WHERE id_movimiento = %s", [id_mov])
    assert con.execute("SELECT count(*) FROM movimiento WHERE id_movimiento = %s", [id_mov]).fetchone()[0] == 1


# =====================================================================
# 5. Movimiento: propiedad (un usuario no usa datos de otro)
# =====================================================================

def test_movimiento_con_cuenta_de_otro_usuario(con, m):
    """CA-06, RN-04."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_cuenta", "movimiento",
                     **fila_mov(m, "EGRESO", id_cuenta=m.cuenta_u2))


def test_movimiento_con_categoria_de_otro_usuario(con, m):
    """CA-06, RN-04. La categoría de U2 es del tipo correcto: solo falla la propiedad."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_categoria", "movimiento",
                     **fila_mov(m, "EGRESO", id_categoria=m.cat_egr_u2))


def test_transferencia_hacia_cuenta_de_otro_usuario(con, m):
    """CA-06, RN-04, RN-33: las transferencias son entre cuentas propias."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_cuenta_destino", "movimiento",
                     **fila_mov(m, "TRANSFERENCIA", id_cuenta_destino=m.cuenta_u2))


def test_movimiento_a_nombre_de_otro_usuario_con_datos_propios(con, m):
    """CA-06 al revés: U2 como dueño de un movimiento que usa la cuenta y la categoría de U1."""
    rechaza_insertar(con, errors.ForeignKeyViolation,
                     ("fk_movimiento_cuenta", "fk_movimiento_categoria"), "movimiento",
                     **fila_mov(m, "EGRESO", id_usuario=m.u2))


# =====================================================================
# 6. Movimiento: tipo de categoría = tipo de movimiento
# =====================================================================

def test_egreso_con_categoria_de_ingreso(con, m):
    """CA-05, RN-31."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_categoria", "movimiento",
                     **fila_mov(m, "EGRESO", id_categoria=m.cat_ing))


def test_ingreso_con_categoria_de_egreso(con, m):
    """CA-05, RN-31."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_categoria", "movimiento",
                     **fila_mov(m, "INGRESO", id_categoria=m.cat_egr))


def test_no_se_puede_reclasificar_un_egreso_a_una_categoria_de_ingreso(con, m):
    """RN-31 también al corregir (RN-72), no solo al crear."""
    id_mov = insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_categoria",
            "UPDATE movimiento SET id_categoria = %s WHERE id_movimiento = %s", [m.cat_ing, id_mov])


def test_no_se_puede_convertir_un_egreso_en_ingreso_dejando_su_categoria(con, m):
    """RN-72: cambiar solo el tipo rompe la correspondencia con la categoría."""
    id_mov = insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_categoria",
            "UPDATE movimiento SET tipo = 'INGRESO' WHERE id_movimiento = %s", [id_mov])


# =====================================================================
# 7. Movimiento: forma de cada tipo (ck_movimiento_forma)
#    Aquí están los casos con NULL, que son los que un CHECK mal escrito deja pasar.
# =====================================================================

@pytest.mark.parametrize("tipo", ["INGRESO", "EGRESO"])
def test_ingreso_o_egreso_sin_categoria(con, m, tipo):
    """RN-30. Caso NULL: con 'id_categoria IN (...)' o sin 'IS NOT NULL' esto pasaría."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, tipo, id_categoria=None))


@pytest.mark.parametrize("tipo", ["INGRESO", "EGRESO", "AJUSTE_AUMENTO", "AJUSTE_DISMINUCION"])
def test_solo_la_transferencia_tiene_cuenta_destino(con, m, tipo):
    """RN-33."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, tipo, id_cuenta_destino=m.nubank))


def test_transferencia_sin_destino(con, m):
    """RN-33. Caso NULL: 'destino <> origen' daría NULL y pasaría sin el IS NOT NULL."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, "TRANSFERENCIA", id_cuenta_destino=None))


def test_transferencia_a_la_misma_cuenta(con, m):
    """RN-33."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, "TRANSFERENCIA", id_cuenta_destino=m.nequi))


@pytest.mark.parametrize("tipo", ["TRANSFERENCIA", "AJUSTE_AUMENTO", "AJUSTE_DISMINUCION"])
def test_transferencias_y_ajustes_no_llevan_categoria(con, m, tipo):
    """RN-33, RN-52. El CHECK se evalúa antes que las FK, por eso el error es del CHECK."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, tipo, id_categoria=m.cat_egr))


@pytest.mark.parametrize("descripcion", [None, "", "    "])
@pytest.mark.parametrize("tipo", ["AJUSTE_AUMENTO", "AJUSTE_DISMINUCION"])
def test_ajuste_sin_motivo(con, m, tipo, descripcion):
    """RN-52: el motivo es obligatorio; NULL, vacío y solo espacios cuentan como 'sin motivo'."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, tipo, descripcion=descripcion))


def test_tipo_de_movimiento_invalido(con, m):
    """D-03. Fallan a la vez el CHECK de tipo y el de forma; cualquiera de los dos es correcto."""
    rechaza_insertar(con, errors.CheckViolation, ("ck_movimiento_tipo", "ck_movimiento_forma"), "movimiento",
                     id_usuario=m.u1, tipo="APARTADO", id_cuenta=m.nequi, monto=Decimal("1000"), fecha=FECHA)


def test_tipo_nulo(con, m):
    """Caso NULL: si tipo admitiera NULL, todos los CHECK darían NULL y la fila pasaría."""
    with pytest.raises(errors.NotNullViolation):
        with con.transaction():
            insertar(con, "movimiento", id_usuario=m.u1, tipo=None, id_cuenta=m.nequi,
                     monto=Decimal("1000"), fecha=FECHA)


# =====================================================================
# 8. Movimiento: monto, estado y fecha
# =====================================================================

@pytest.mark.parametrize("monto", ["0", "-1", "-0.01", "0.004"])
def test_monto_cero_o_negativo(con, m, monto):
    """RN-30. Caso límite: 0.004 se redondea a 0.00 antes de evaluar el CHECK."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_monto", "movimiento",
                     **fila_mov(m, "EGRESO", monto=Decimal(monto)))


def test_monto_minimo_y_redondeo(con, m):
    """Caso límite: 0.01 es válido y 0.005 se guarda como 0.01 (dos decimales)."""
    insertar(con, "movimiento", **fila_mov(m, "EGRESO", monto=Decimal("0.01")))
    id_mov = insertar(con, "movimiento", **fila_mov(m, "EGRESO", monto=Decimal("0.005")))
    assert con.execute("SELECT monto FROM movimiento WHERE id_movimiento = %s", [id_mov]).fetchone()[0] == Decimal("0.01")


def test_monto_demasiado_grande(con, m):
    """numeric(14,2) admite hasta 999.999.999.999,99."""
    insertar(con, "movimiento", **fila_mov(m, "EGRESO", monto=Decimal("999999999999.99")))
    with pytest.raises(errors.NumericValueOutOfRange):
        with con.transaction():
            insertar(con, "movimiento", **fila_mov(m, "EGRESO", monto=Decimal("1000000000000")))


@pytest.mark.parametrize("estado", ["PENDIENTE", "anulado", ""])
def test_estado_invalido(con, m, estado):
    """RN-70: solo VIGENTE y ANULADO."""
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_estado", "movimiento",
                     **fila_mov(m, "EGRESO", estado=estado))


@pytest.mark.parametrize("columna", ["monto", "fecha", "id_cuenta", "id_usuario"])
def test_datos_obligatorios_del_movimiento(con, m, columna):
    """RN-30."""
    with pytest.raises(errors.NotNullViolation):
        with con.transaction():
            insertar(con, "movimiento", **fila_mov(m, "EGRESO", **{columna: None}))


# =====================================================================
# 9. Transferencias y cargos
# =====================================================================

def test_transferencia_con_cargo_ca02(con, m):
    """CA-02, RN-33 a RN-35: 200.000 de Nequi a Nubank con cargo de 800.
    La transferencia es UNA fila; el cargo es un EGRESO que apunta a ella."""
    transferencia = nueva_transferencia(con, m)
    cargo = insertar(con, "movimiento", **fila_mov(
        m, "EGRESO", id_categoria=m.cat_cargos, id_transferencia=transferencia, monto=Decimal("800")))

    sale_de_nequi, entra_a_nubank, egresos = con.execute(
        """
        SELECT sum(monto) FILTER (WHERE id_cuenta = %(nequi)s AND tipo IN ('TRANSFERENCIA', 'EGRESO')),
               sum(monto) FILTER (WHERE id_cuenta_destino = %(nubank)s),
               sum(monto) FILTER (WHERE tipo = 'EGRESO')
          FROM movimiento
         WHERE id_usuario = %(u)s AND estado = 'VIGENTE'
        """,
        {"nequi": m.nequi, "nubank": m.nubank, "u": m.u1},
    ).fetchone()
    assert (sale_de_nequi, entra_a_nubank, egresos) == (Decimal("200800.00"), Decimal("200000.00"), Decimal("800.00"))
    assert cargo != transferencia


def test_transferencia_con_varios_cargos(con, m):
    """RN-34: cero o más cargos por transferencia."""
    transferencia = nueva_transferencia(con, m)
    for monto in ("800", "3500"):
        insertar(con, "movimiento", **fila_mov(
            m, "EGRESO", id_categoria=m.cat_cargos, id_transferencia=transferencia, monto=Decimal(monto)))
    cantidad = con.execute(
        "SELECT count(*) FROM movimiento WHERE id_transferencia = %s", [transferencia]).fetchone()[0]
    assert cantidad == 2


def test_cargo_desde_una_cuenta_distinta_a_la_de_origen(con, m):
    """RN-35: el cargo sale de la cuenta de origen. Aquí se intenta desde la de DESTINO."""
    transferencia = nueva_transferencia(con, m)
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_transferencia", "movimiento",
                     **fila_mov(m, "EGRESO", id_cuenta=m.nubank, id_categoria=m.cat_cargos,
                                id_transferencia=transferencia))


def test_cargo_que_apunta_a_la_transferencia_de_otro_usuario(con, m):
    """CA-06, RN-04: todo lo demás del egreso de U2 es válido y propio."""
    transferencia_u1 = nueva_transferencia(con, m)
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_transferencia", "movimiento",
                     id_usuario=m.u2, tipo="EGRESO", id_cuenta=m.cuenta_u2, id_categoria=m.cat_egr_u2,
                     id_transferencia=transferencia_u1, monto=Decimal("800"), fecha=FECHA)


def test_cargo_que_apunta_a_un_movimiento_inexistente(con, m):
    """RN-34: la transferencia apuntada debe existir."""
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_movimiento_transferencia", "movimiento",
                     **fila_mov(m, "EGRESO", id_transferencia=-1))


@pytest.mark.parametrize("tipo", ["INGRESO", "TRANSFERENCIA", "AJUSTE_AUMENTO", "AJUSTE_DISMINUCION"])
def test_solo_un_egreso_puede_ser_cargo(con, m, tipo):
    """RN-34: un ingreso, otra transferencia o un ajuste no pueden ser 'cargo'."""
    transferencia = nueva_transferencia(con, m)
    rechaza_insertar(con, errors.CheckViolation, "ck_movimiento_forma", "movimiento",
                     **fila_mov(m, tipo, id_transferencia=transferencia))


def test_un_movimiento_no_puede_ser_cargo_de_si_mismo(con, m):
    """Caso límite: la FK lo aceptaría (mismo usuario, misma cuenta); lo impide el CHECK."""
    egreso = insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    rechaza(con, errors.CheckViolation, "ck_movimiento_cargo_distinto",
            "UPDATE movimiento SET id_transferencia = id_movimiento WHERE id_movimiento = %s", [egreso])


def test_no_se_puede_cambiar_la_cuenta_de_origen_de_una_transferencia_con_cargos(con, m):
    """RN-72: los cargos dejarían de salir de la cuenta de origen."""
    transferencia = nueva_transferencia(con, m)
    insertar(con, "movimiento", **fila_mov(m, "EGRESO", id_categoria=m.cat_cargos, id_transferencia=transferencia))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_transferencia",
            "UPDATE movimiento SET id_cuenta = %s WHERE id_movimiento = %s", [m.efectivo, transferencia])


def test_no_se_puede_mover_un_cargo_a_otra_cuenta(con, m):
    """RN-35 también al corregir el cargo, no solo al crearlo."""
    transferencia = nueva_transferencia(con, m)
    cargo = insertar(con, "movimiento", **fila_mov(m, "EGRESO", id_categoria=m.cat_cargos, id_transferencia=transferencia))
    rechaza(con, errors.ForeignKeyViolation, "fk_movimiento_transferencia",
            "UPDATE movimiento SET id_cuenta = %s WHERE id_movimiento = %s", [m.efectivo, cargo])


def test_transferencia_sin_cargos_si_puede_cambiar_de_cuenta_de_origen(con, m):
    """Control de la prueba anterior: sin cargos, la corrección es válida (RN-72)."""
    transferencia = nueva_transferencia(con, m)
    con.execute("UPDATE movimiento SET id_cuenta = %s WHERE id_movimiento = %s", [m.efectivo, transferencia])


def test_limite_conocido_la_base_acepta_un_cargo_que_apunta_a_un_egreso(con, m):
    """LÍMITE CONOCIDO (RN-34): la base comprueba usuario y cuenta, pero NO que el
    movimiento apuntado sea una TRANSFERENCIA. Lo debe garantizar el servicio de
    transferencias, que es el único que crea cargos. Si algún día se agrega esa
    restricción a la base, esta prueba debe invertirse."""
    egreso = insertar(con, "movimiento", **fila_mov(m, "EGRESO"))
    assert insertar(con, "movimiento", **fila_mov(m, "EGRESO", id_transferencia=egreso))


# =====================================================================
# 10. Bolsillos y su historial
# =====================================================================

def test_bolsillo_generico_y_bolsillo_con_meta(con, m):
    """Control. RN-41, D-08: la modalidad se deduce de monto_objetivo."""
    generico = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Imprevistos")
    con_meta = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Computador",
                        monto_objetivo=Decimal("3000000"), fecha_objetivo=date(2027, 6, 30))
    sin_fecha = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje", monto_objetivo=Decimal("1000000"))
    assert generico and con_meta and sin_fecha


@pytest.mark.parametrize("objetivo", ["0", "-1", "0.004"])
def test_monto_objetivo_cero_o_negativo(con, m, objetivo):
    """RN-41: si hay meta, es mayor que cero."""
    rechaza_insertar(con, errors.CheckViolation, "ck_bolsillo_monto_objetivo", "bolsillo",
                     id_usuario=m.u1, nombre="Meta rara", monto_objetivo=Decimal(objetivo))


def test_fecha_objetivo_sin_monto_objetivo(con, m):
    """RN-41."""
    rechaza_insertar(con, errors.CheckViolation, "ck_bolsillo_fecha_objetivo", "bolsillo",
                     id_usuario=m.u1, nombre="Sin meta", fecha_objetivo=date(2027, 1, 1))


def test_no_se_puede_quitar_la_meta_dejando_la_fecha(con, m):
    """RN-41 también al editar: convertir en genérico exige quitar también la fecha."""
    bolsillo = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Computador",
                        monto_objetivo=Decimal("3000000"), fecha_objetivo=date(2027, 6, 30))
    rechaza(con, errors.CheckViolation, "ck_bolsillo_fecha_objetivo",
            "UPDATE bolsillo SET monto_objetivo = NULL WHERE id_bolsillo = %s", [bolsillo])


@pytest.mark.parametrize("nombre", ["", "  ", " Viaje", "Viaje "])
def test_nombre_de_bolsillo_vacio_o_con_espacios_extremos(con, m, nombre):
    """MODELO_DATOS 4.5: nombre no vacío y sin espacios al inicio ni al final."""
    rechaza_insertar(con, errors.CheckViolation, "ck_bolsillo_nombre", "bolsillo",
                     id_usuario=m.u1, nombre=nombre)


def test_nombre_de_bolsillo_repetido_entre_activos(con, m):
    """MODELO_DATOS 4.5: nombre único entre los bolsillos activos del usuario, sin distinguir mayúsculas."""
    insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje")
    rechaza_insertar(con, errors.UniqueViolation, "uq_bolsillo_nombre_activo", "bolsillo",
                     id_usuario=m.u1, nombre="VIAJE")
    insertar(con, "bolsillo", id_usuario=m.u2, nombre="Viaje")  # otro usuario: permitido


def test_bolsillo_archivado_libera_el_nombre(con, m):
    """RN-49."""
    viejo = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje")
    con.execute("UPDATE bolsillo SET activo = false WHERE id_bolsillo = %s", [viejo])
    insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje")


def test_valor_de_bolsillo_negativo(con, m):
    """CA-08, RN-43."""
    bolsillo = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje")
    rechaza_insertar(con, errors.CheckViolation, "ck_bolsillo_valor_no_negativo", "bolsillo_valor",
                     id_usuario=m.u1, id_bolsillo=bolsillo, valor=Decimal("-0.01"))


def test_valor_de_bolsillo_cero_y_mayor_que_la_meta(con, m):
    """RN-43, RN-48: cero se permite, y el valor puede superar el objetivo (más del 100 %)."""
    bolsillo = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje", monto_objetivo=Decimal("1000"))
    insertar(con, "bolsillo_valor", id_usuario=m.u1, id_bolsillo=bolsillo, valor=Decimal("0"))
    insertar(con, "bolsillo_valor", id_usuario=m.u1, id_bolsillo=bolsillo, valor=Decimal("5000"))


def test_historial_con_el_bolsillo_de_otro_usuario(con, m):
    """CA-06, RN-04: U2 no puede escribir en el historial de un bolsillo de U1."""
    bolsillo_u1 = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Viaje")
    rechaza_insertar(con, errors.ForeignKeyViolation, "fk_bolsillo_valor_bolsillo", "bolsillo_valor",
                     id_usuario=m.u2, id_bolsillo=bolsillo_u1, valor=Decimal("100"))


def test_valor_actual_es_el_registro_mas_reciente(con, m):
    """CA-07, RN-44. Caso límite: los tres registros se insertan en la MISMA transacción,
    así que tienen la misma fecha y hora (now() es la hora de inicio de la transacción).
    El desempate debe ser por id_bolsillo_valor."""
    bolsillo = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Computador", monto_objetivo=Decimal("1000000"))
    for valor in ("0", "500000", "350000"):
        insertar(con, "bolsillo_valor", id_usuario=m.u1, id_bolsillo=bolsillo, valor=Decimal(valor))

    consulta = """
        SELECT DISTINCT ON (v.id_bolsillo) v.valor, b.monto_objetivo
          FROM bolsillo_valor v
          JOIN bolsillo b ON b.id_bolsillo = v.id_bolsillo
         WHERE v.id_usuario = %s AND v.id_bolsillo = %s
         ORDER BY v.id_bolsillo, v.registrado_en DESC, v.id_bolsillo_valor DESC
    """
    valor, objetivo = con.execute(consulta, [m.u1, bolsillo]).fetchone()
    assert valor == Decimal("350000.00")
    assert valor * 100 / objetivo == Decimal("35")  # progreso 35 %

    # Un registro insertado después pero con fecha ANTERIOR no es el valor actual:
    # manda la fecha; el id solo desempata.
    ayer = con.execute("SELECT now()").fetchone()[0] - timedelta(days=1)
    insertar(con, "bolsillo_valor", id_usuario=m.u1, id_bolsillo=bolsillo, valor=Decimal("999"), registrado_en=ayer)
    assert con.execute(consulta, [m.u1, bolsillo]).fetchone()[0] == Decimal("350000.00")
    assert con.execute("SELECT count(*) FROM bolsillo_valor WHERE id_bolsillo = %s", [bolsillo]).fetchone()[0] == 4


def test_cambiar_un_bolsillo_no_toca_los_movimientos(con, m):
    """CA-07, CA-09, RN-39, RN-47: bolsillos y movimientos son independientes."""
    bolsillo = insertar(con, "bolsillo", id_usuario=m.u1, nombre="Computador")
    insertar(con, "bolsillo_valor", id_usuario=m.u1, id_bolsillo=bolsillo, valor=Decimal("200000"))
    antes = con.execute("SELECT count(*) FROM movimiento WHERE id_usuario = %s", [m.u1]).fetchone()[0]

    nueva_transferencia(con, m, monto="100000")
    valor = con.execute(
        "SELECT valor FROM bolsillo_valor WHERE id_bolsillo = %s ORDER BY registrado_en DESC, id_bolsillo_valor DESC LIMIT 1",
        [bolsillo],
    ).fetchone()[0]
    assert valor == Decimal("200000.00")  # la transferencia no cambió la reserva
    assert con.execute("SELECT count(*) FROM movimiento WHERE id_usuario = %s", [m.u1]).fetchone()[0] == antes + 1
