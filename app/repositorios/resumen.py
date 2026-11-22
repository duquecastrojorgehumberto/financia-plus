"""Consultas del resumen financiero (RF-15). Solo lectura.

El saldo total y el total reservado no tienen consulta propia: se calculan con
las de CuentaRepositorio y BolsilloRepositorio (el mismo cálculo que ya se
usa y se prueba en otras pantallas; ver ResumenServicio).
"""

from datetime import date
from decimal import Decimal

import psycopg


class ResumenRepositorio:
    def __init__(self, con: psycopg.Connection):
        self.con = con

    def totales_por_tipo(self, id_usuario: int, desde: date, hasta: date) -> dict[str, Decimal]:
        """Suma de los movimientos VIGENTES del periodo, por tipo (RN-64).

        Devuelve, por ejemplo, {"INGRESO": 50000, "EGRESO": 20800, "AJUSTE_DISMINUCION": 6500}.
        Un tipo sin movimientos no aparece. Las transferencias se suman aquí, pero
        el servicio no las usa: no son ingreso ni gasto (RN-33).
        """
        filas = self.con.execute(
            """
            SELECT tipo, SUM(monto) AS total
              FROM movimiento
             WHERE id_usuario = %s
               AND estado = 'VIGENTE'
               AND fecha BETWEEN %s AND %s
             GROUP BY tipo
            """,
            (id_usuario, desde, hasta),
        ).fetchall()
        return {f["tipo"]: f["total"] for f in filas}

    def totales_por_categoria(self, id_usuario: int, desde: date, hasta: date) -> list[dict]:
        """Total de ingresos y egresos VIGENTES del periodo por categoría (la que tiene cada movimiento).

        Cada fila trae también la raíz de la categoría (ella misma si es raíz),
        para que el servicio consolide las subcategorías en su raíz (RN-27).
        Cada movimiento tiene UNA categoría (D-06), así que se cuenta una sola vez.
        Incluye categorías ya desactivadas: sus movimientos siguen contando (CA-14).
        """
        return self.con.execute(
            """
            SELECT cat.id_categoria,
                   cat.nombre,
                   cat.tipo,
                   cat.id_padre,
                   COALESCE(raiz.id_categoria, cat.id_categoria) AS id_raiz,
                   COALESCE(raiz.nombre, cat.nombre)             AS nombre_raiz,
                   SUM(m.monto)                                  AS total
              FROM movimiento m
              JOIN categoria cat
                ON cat.id_usuario = m.id_usuario AND cat.id_categoria = m.id_categoria
              LEFT JOIN categoria raiz
                ON raiz.id_usuario = cat.id_usuario AND raiz.id_categoria = cat.id_padre
             WHERE m.id_usuario = %s
               AND m.estado = 'VIGENTE'
               AND m.tipo IN ('INGRESO', 'EGRESO')
               AND m.fecha BETWEEN %s AND %s
             GROUP BY cat.id_categoria, raiz.id_categoria
            """,
            (id_usuario, desde, hasta),
        ).fetchall()
