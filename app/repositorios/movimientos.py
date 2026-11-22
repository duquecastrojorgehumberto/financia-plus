"""SQL de la tabla movimiento."""

from datetime import date
from decimal import Decimal

import psycopg

from app.entidades.movimiento import EstadoMovimiento, Movimiento, MovimientoDetalle, TipoMovimiento


class MovimientoRepositorio:
    def __init__(self, con: psycopg.Connection):
        self.con = con

    @staticmethod
    def _a_movimiento(fila: dict) -> Movimiento:
        return Movimiento(
            id_movimiento=fila["id_movimiento"],
            id_usuario=fila["id_usuario"],
            tipo=TipoMovimiento(fila["tipo"]),
            id_cuenta=fila["id_cuenta"],
            id_cuenta_destino=fila["id_cuenta_destino"],
            id_categoria=fila["id_categoria"],
            id_transferencia=fila["id_transferencia"],
            monto=fila["monto"],
            fecha=fila["fecha"],
            descripcion=fila["descripcion"],
            estado=EstadoMovimiento(fila["estado"]),
            creado_en=fila["creado_en"],
            actualizado_en=fila["actualizado_en"],
        )

    @classmethod
    def _a_detalle(cls, fila: dict) -> MovimientoDetalle:
        return MovimientoDetalle(
            movimiento=cls._a_movimiento(fila),
            nombre_cuenta=fila["nombre_cuenta"],
            nombre_cuenta_destino=fila["nombre_cuenta_destino"],
            nombre_categoria=fila["nombre_categoria"],
        )

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def listar(self, id_usuario: int, *, desde: date | None = None, hasta: date | None = None,
               id_cuenta: int | None = None, tipo: str | None = None,
               id_categoria: int | None = None, estado: str | None = None,
               id_movimiento: int | None = None) -> list[MovimientoDetalle]:
        """Historial con filtros opcionales (RF-14). Un filtro en None no se aplica.

        Cada filtro es "(%(filtro)s IS NULL OR condición)": si el valor es NULL,
        la condición se da por cumplida. Así hay UNA sola consulta, escrita
        completa, y todos los valores van como parámetros.

          * id_cuenta:     la cuenta como origen O como destino (una transferencia
                           que entra también es parte de su historial).
          * id_categoria:  esa categoría Y sus subcategorías.
          * id_movimiento: uno solo (lo usa obtener_detalle).

        Los nombres de cuenta y categoría vienen con LEFT JOIN porque destino y
        categoría pueden ser NULL. Los JOIN también comparan id_usuario.
        """
        filas = self.con.execute(
            """
            SELECT m.id_movimiento, m.id_usuario, m.tipo, m.id_cuenta, m.id_cuenta_destino,
                   m.id_categoria, m.id_transferencia, m.monto, m.fecha, m.descripcion,
                   m.estado, m.creado_en, m.actualizado_en,
                   c.nombre   AS nombre_cuenta,
                   d.nombre   AS nombre_cuenta_destino,
                   cat.nombre AS nombre_categoria
              FROM movimiento m
              JOIN cuenta c
                ON c.id_usuario = m.id_usuario AND c.id_cuenta = m.id_cuenta
              LEFT JOIN cuenta d
                ON d.id_usuario = m.id_usuario AND d.id_cuenta = m.id_cuenta_destino
              LEFT JOIN categoria cat
                ON cat.id_usuario = m.id_usuario AND cat.id_categoria = m.id_categoria
             WHERE m.id_usuario = %(id_usuario)s
               AND (%(id_movimiento)s::bigint IS NULL OR m.id_movimiento = %(id_movimiento)s)
               AND (%(desde)s::date IS NULL OR m.fecha >= %(desde)s)
               AND (%(hasta)s::date IS NULL OR m.fecha <= %(hasta)s)
               AND (%(id_cuenta)s::bigint IS NULL
                    OR m.id_cuenta = %(id_cuenta)s
                    OR m.id_cuenta_destino = %(id_cuenta)s)
               AND (%(tipo)s::text IS NULL OR m.tipo = %(tipo)s)
               AND (%(estado)s::text IS NULL OR m.estado = %(estado)s)
               AND (%(id_categoria)s::bigint IS NULL
                    OR m.id_categoria = %(id_categoria)s
                    OR cat.id_padre = %(id_categoria)s)
             ORDER BY m.fecha DESC, m.id_movimiento DESC
            """,
            {"id_usuario": id_usuario, "id_movimiento": id_movimiento, "desde": desde, "hasta": hasta,
             "id_cuenta": id_cuenta, "tipo": tipo, "estado": estado, "id_categoria": id_categoria},
        ).fetchall()
        return [self._a_detalle(f) for f in filas]

    def obtener_detalle(self, id_usuario: int, id_movimiento: int) -> MovimientoDetalle | None:
        filas = self.listar(id_usuario, id_movimiento=id_movimiento)
        return filas[0] if filas else None

    def obtener_para_actualizar(self, id_usuario: int, id_movimiento: int) -> Movimiento | None:
        """Lee el movimiento y bloquea su fila hasta el final de la transacción (FOR UPDATE)."""
        fila = self.con.execute(
            """
            SELECT id_movimiento, id_usuario, tipo, id_cuenta, id_cuenta_destino, id_categoria,
                   id_transferencia, monto, fecha, descripcion, estado, creado_en, actualizado_en
              FROM movimiento
             WHERE id_usuario = %s
               AND id_movimiento = %s
               FOR UPDATE
            """,
            (id_usuario, id_movimiento),
        ).fetchone()
        return self._a_movimiento(fila) if fila else None

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def insertar_ingreso_o_egreso(self, id_usuario: int, tipo: TipoMovimiento, id_cuenta: int,
                                  id_categoria: int, monto: Decimal, fecha: date,
                                  descripcion: str | None) -> Movimiento:
        fila = self.con.execute(
            """
            INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, monto, fecha, descripcion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_movimiento, id_usuario, tipo, id_cuenta, id_cuenta_destino, id_categoria,
                      id_transferencia, monto, fecha, descripcion, estado, creado_en, actualizado_en
            """,
            (id_usuario, str(tipo), id_cuenta, id_categoria, monto, fecha, descripcion),
        ).fetchone()
        return self._a_movimiento(fila)

    def corregir(self, id_usuario: int, id_movimiento: int, id_cuenta: int, id_categoria: int,
                 monto: Decimal, fecha: date, descripcion: str | None) -> None:
        """RN-72 y RN-73: cambia los datos corregibles y marca actualizado_en. El tipo no se toca."""
        self.con.execute(
            """
            UPDATE movimiento
               SET id_cuenta = %s, id_categoria = %s, monto = %s, fecha = %s, descripcion = %s,
                   actualizado_en = now()
             WHERE id_usuario = %s
               AND id_movimiento = %s
            """,
            (id_cuenta, id_categoria, monto, fecha, descripcion, id_usuario, id_movimiento),
        )

    def cambiar_estado(self, id_usuario: int, id_movimiento: int, estado: EstadoMovimiento) -> None:
        """Anular o reactivar (RN-70, RN-71). Nunca se borra la fila."""
        self.con.execute(
            """
            UPDATE movimiento
               SET estado = %s, actualizado_en = now()
             WHERE id_usuario = %s
               AND id_movimiento = %s
            """,
            (str(estado), id_usuario, id_movimiento),
        )
