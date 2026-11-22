"""SQL de las tablas bolsillo y bolsillo_valor.

El valor actual de un bolsillo es su registro más reciente en bolsillo_valor
(D-09): mayor registrado_en y, si hay empate, mayor id_bolsillo_valor. Se
obtiene con DISTINCT ON, que deja UNA fila por bolsillo: la primera según el
ORDER BY. El índice ix_bolsillo_valor_reciente tiene justo ese orden.

¿Por qué el desempate? registrado_en toma now(), que es la hora de INICIO de
la transacción: dos valores guardados en la misma transacción (por ejemplo,
crear el bolsillo y cambiarle el valor enseguida) quedan con la misma hora.
"""

from datetime import date
from decimal import Decimal

import psycopg

from app.entidades.bolsillo import Bolsillo, BolsilloConValor, ValorBolsillo


class BolsilloRepositorio:
    def __init__(self, con: psycopg.Connection):
        self.con = con

    @staticmethod
    def _a_bolsillo(fila: dict) -> Bolsillo:
        return Bolsillo(
            id_bolsillo=fila["id_bolsillo"],
            id_usuario=fila["id_usuario"],
            nombre=fila["nombre"],
            descripcion=fila["descripcion"],
            monto_objetivo=fila["monto_objetivo"],
            fecha_objetivo=fila["fecha_objetivo"],
            activo=fila["activo"],
            creado_en=fila["creado_en"],
        )

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def listar_con_valor(self, id_usuario: int, *, incluir_archivados: bool,
                         id_bolsillo: int | None = None) -> list[BolsilloConValor]:
        """Bolsillos con su valor actual. Con id_bolsillo, solo ese.

        JOIN (no LEFT JOIN): todo bolsillo tiene al menos un valor, porque se
        crea junto con el primero en la misma transacción (RN-45).
        """
        filas = self.con.execute(
            """
            SELECT b.id_bolsillo, b.id_usuario, b.nombre, b.descripcion, b.monto_objetivo,
                   b.fecha_objetivo, b.activo, b.creado_en,
                   v.valor AS valor_actual
              FROM bolsillo b
              JOIN (SELECT DISTINCT ON (id_bolsillo) id_bolsillo, valor
                      FROM bolsillo_valor
                     WHERE id_usuario = %(id_usuario)s
                     ORDER BY id_bolsillo, registrado_en DESC, id_bolsillo_valor DESC) v
                ON v.id_bolsillo = b.id_bolsillo
             WHERE b.id_usuario = %(id_usuario)s
               AND (%(id_bolsillo)s::bigint IS NULL OR b.id_bolsillo = %(id_bolsillo)s)
               AND (b.activo OR %(archivados)s)
             ORDER BY b.activo DESC, lower(b.nombre)
            """,
            {"id_usuario": id_usuario, "id_bolsillo": id_bolsillo, "archivados": incluir_archivados},
        ).fetchall()
        return [BolsilloConValor(self._a_bolsillo(f), f["valor_actual"]) for f in filas]

    def obtener_con_valor(self, id_usuario: int, id_bolsillo: int) -> BolsilloConValor | None:
        filas = self.listar_con_valor(id_usuario, incluir_archivados=True, id_bolsillo=id_bolsillo)
        return filas[0] if filas else None

    def historial(self, id_usuario: int, id_bolsillo: int) -> list[ValorBolsillo]:
        """Todos los valores, del más reciente al más antiguo (RF-12)."""
        filas = self.con.execute(
            """
            SELECT id_bolsillo_valor, id_bolsillo, valor, registrado_en
              FROM bolsillo_valor
             WHERE id_usuario = %s
               AND id_bolsillo = %s
             ORDER BY registrado_en DESC, id_bolsillo_valor DESC
            """,
            (id_usuario, id_bolsillo),
        ).fetchall()
        return [ValorBolsillo(**f) for f in filas]

    def obtener_para_actualizar(self, id_usuario: int, id_bolsillo: int) -> Bolsillo | None:
        """Lee el bolsillo y bloquea su fila hasta el final de la transacción (FOR UPDATE)."""
        fila = self.con.execute(
            """
            SELECT id_bolsillo, id_usuario, nombre, descripcion, monto_objetivo, fecha_objetivo,
                   activo, creado_en
              FROM bolsillo
             WHERE id_usuario = %s
               AND id_bolsillo = %s
               FOR UPDATE
            """,
            (id_usuario, id_bolsillo),
        ).fetchone()
        return self._a_bolsillo(fila) if fila else None

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def insertar(self, id_usuario: int, nombre: str, descripcion: str | None,
                 monto_objetivo: Decimal | None, fecha_objetivo: date | None) -> Bolsillo:
        fila = self.con.execute(
            """
            INSERT INTO bolsillo (id_usuario, nombre, descripcion, monto_objetivo, fecha_objetivo)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_bolsillo, id_usuario, nombre, descripcion, monto_objetivo, fecha_objetivo,
                      activo, creado_en
            """,
            (id_usuario, nombre, descripcion, monto_objetivo, fecha_objetivo),
        ).fetchone()
        return self._a_bolsillo(fila)

    def insertar_valor(self, id_usuario: int, id_bolsillo: int, valor: Decimal) -> None:
        """RN-44: cada cambio AGREGA un registro. Esta tabla nunca se modifica (D-15: el rol
        de la aplicación ni siquiera tiene permiso UPDATE sobre ella)."""
        self.con.execute(
            "INSERT INTO bolsillo_valor (id_usuario, id_bolsillo, valor) VALUES (%s, %s, %s)",
            (id_usuario, id_bolsillo, valor),
        )

    def actualizar(self, id_usuario: int, id_bolsillo: int, nombre: str, descripcion: str | None,
                   monto_objetivo: Decimal | None, fecha_objetivo: date | None) -> None:
        self.con.execute(
            """
            UPDATE bolsillo
               SET nombre = %s, descripcion = %s, monto_objetivo = %s, fecha_objetivo = %s
             WHERE id_usuario = %s
               AND id_bolsillo = %s
            """,
            (nombre, descripcion, monto_objetivo, fecha_objetivo, id_usuario, id_bolsillo),
        )

    def cambiar_activo(self, id_usuario: int, id_bolsillo: int, activo: bool) -> None:
        """Archivar (False) o reactivar (True). Nunca se borra (RN-49)."""
        self.con.execute(
            "UPDATE bolsillo SET activo = %s WHERE id_usuario = %s AND id_bolsillo = %s",
            (activo, id_usuario, id_bolsillo),
        )
