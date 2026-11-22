"""SQL de la tabla cuenta, incluida la consulta del saldo calculado.

Fórmula del saldo (REGLAS_NEGOCIO.md, sección 2; solo movimientos VIGENTES):

    saldo = saldo_inicial
          + INGRESOS                        - EGRESOS (incluye cargos de transferencias)
          - TRANSFERENCIAS que salen        + TRANSFERENCIAS que entran
          + AJUSTES_AUMENTO                 - AJUSTES_DISMINUCION

En SQL: se une cada cuenta con los movimientos donde aparece como origen
(id_cuenta) o como destino (id_cuenta_destino), y un CASE decide si cada
movimiento suma o resta. Una transferencia aparece una vez en la cuenta de
origen (resta) y otra en la de destino (suma), porque origen y destino son
distintos (ck_movimiento_forma). LEFT JOIN: una cuenta sin movimientos
también aparece; SUM da NULL y COALESCE lo vuelve 0.
"""

from decimal import Decimal

import psycopg

from app.entidades.cuenta import Cuenta, CuentaConSaldo, TipoCuenta

class CuentaRepositorio:
    def __init__(self, con: psycopg.Connection):
        self.con = con

    @staticmethod
    def _a_cuenta(fila: dict) -> Cuenta:
        return Cuenta(
            id_cuenta=fila["id_cuenta"],
            id_usuario=fila["id_usuario"],
            nombre=fila["nombre"],
            tipo=TipoCuenta(fila["tipo"]),
            saldo_inicial=fila["saldo_inicial"],
            activa=fila["activa"],
            creado_en=fila["creado_en"],
        )

    @classmethod
    def _a_cuenta_con_saldo(cls, fila: dict) -> CuentaConSaldo:
        return CuentaConSaldo(cuenta=cls._a_cuenta(fila), saldo=fila["saldo"])

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def _consultar_con_saldo(self, id_usuario: int, id_cuenta: int | None,
                             incluir_archivadas: bool) -> list[dict]:
        """La consulta del saldo, escrita una sola vez.

        Los dos filtros opcionales también son parámetros:
          * %(id_cuenta)s IS NULL       -> todas las cuentas; si trae un número, solo esa.
          * c.activa OR %(archivadas)s  -> si archivadas es true, también las archivadas.
        """
        return self.con.execute(
            """
            SELECT c.id_cuenta, c.id_usuario, c.nombre, c.tipo, c.saldo_inicial, c.activa, c.creado_en,
                   c.saldo_inicial + COALESCE(SUM(
                     CASE
                       WHEN m.id_cuenta_destino = c.id_cuenta          THEN  m.monto  -- transferencia que entra
                       WHEN m.tipo = 'TRANSFERENCIA'                   THEN -m.monto  -- transferencia que sale
                       WHEN m.tipo IN ('INGRESO', 'AJUSTE_AUMENTO')    THEN  m.monto
                       WHEN m.tipo IN ('EGRESO', 'AJUSTE_DISMINUCION') THEN -m.monto
                     END), 0) AS saldo
              FROM cuenta c
              LEFT JOIN movimiento m
                     ON m.id_usuario = c.id_usuario
                    AND m.estado = 'VIGENTE'
                    AND (m.id_cuenta = c.id_cuenta OR m.id_cuenta_destino = c.id_cuenta)
             WHERE c.id_usuario = %(id_usuario)s
               AND (%(id_cuenta)s::bigint IS NULL OR c.id_cuenta = %(id_cuenta)s)
               AND (c.activa OR %(archivadas)s)
             GROUP BY c.id_cuenta
             ORDER BY c.activa DESC, lower(c.nombre)
            """,
            {"id_usuario": id_usuario, "id_cuenta": id_cuenta, "archivadas": incluir_archivadas},
        ).fetchall()

    def listar_con_saldo(self, id_usuario: int, incluir_archivadas: bool) -> list[CuentaConSaldo]:
        filas = self._consultar_con_saldo(id_usuario, None, incluir_archivadas)
        return [self._a_cuenta_con_saldo(f) for f in filas]

    def obtener_con_saldo(self, id_usuario: int, id_cuenta: int) -> CuentaConSaldo | None:
        filas = self._consultar_con_saldo(id_usuario, id_cuenta, True)
        return self._a_cuenta_con_saldo(filas[0]) if filas else None

    def obtener_para_actualizar(self, id_usuario: int, id_cuenta: int) -> Cuenta | None:
        """Lee la cuenta y BLOQUEA su fila hasta el final de la transacción (FOR UPDATE).

        Mientras esté bloqueada, nadie puede registrar un movimiento en ella:
        insertar un movimiento revisa la FK hacia cuenta, y esa revisión
        (FOR KEY SHARE) tiene que esperar a que termine este bloqueo. Así el
        saldo que se calcula después no cambia antes del COMMIT (RN-12, RN-55).
        Solo tiene sentido dentro de "with con.transaction():".
        """
        fila = self.con.execute(
            """
            SELECT id_cuenta, id_usuario, nombre, tipo, saldo_inicial, activa, creado_en
              FROM cuenta
             WHERE id_usuario = %s
               AND id_cuenta = %s
               FOR UPDATE
            """,
            (id_usuario, id_cuenta),
        ).fetchone()
        return self._a_cuenta(fila) if fila else None

    def obtener_para_usar(self, id_usuario: int, id_cuenta: int) -> Cuenta | None:
        """Lee la cuenta con un bloqueo COMPARTIDO (FOR SHARE) hasta el final de la transacción.

        Se usa al registrar o cambiar un movimiento: varias transacciones pueden
        tener a la vez este bloqueo (no se estorban entre sí), pero archivar la
        cuenta (FOR UPDATE) tiene que esperar a que terminen, y viceversa. Así la
        cuenta no se archiva entre "revisé que está activa" y el INSERT.
        """
        fila = self.con.execute(
            """
            SELECT id_cuenta, id_usuario, nombre, tipo, saldo_inicial, activa, creado_en
              FROM cuenta
             WHERE id_usuario = %s
               AND id_cuenta = %s
               FOR SHARE
            """,
            (id_usuario, id_cuenta),
        ).fetchone()
        return self._a_cuenta(fila) if fila else None

    def tiene_movimientos(self, id_usuario: int, id_cuenta: int) -> bool:
        """True si la cuenta aparece en algún movimiento, como origen o destino, VIGENTE o ANULADO."""
        fila = self.con.execute(
            """
            SELECT EXISTS (
              SELECT 1
                FROM movimiento
               WHERE id_usuario = %s
                 AND (id_cuenta = %s OR id_cuenta_destino = %s)
            ) AS hay
            """,
            (id_usuario, id_cuenta, id_cuenta),
        ).fetchone()
        return fila["hay"]

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def insertar(self, id_usuario: int, nombre: str, tipo: TipoCuenta, saldo_inicial: Decimal) -> Cuenta:
        fila = self.con.execute(
            """
            INSERT INTO cuenta (id_usuario, nombre, tipo, saldo_inicial)
            VALUES (%s, %s, %s, %s)
            RETURNING id_cuenta, id_usuario, nombre, tipo, saldo_inicial, activa, creado_en
            """,
            (id_usuario, nombre, str(tipo), saldo_inicial),
        ).fetchone()
        return self._a_cuenta(fila)

    def actualizar(self, id_usuario: int, id_cuenta: int, nombre: str, tipo: TipoCuenta,
                   saldo_inicial: Decimal) -> None:
        self.con.execute(
            """
            UPDATE cuenta
               SET nombre = %s, tipo = %s, saldo_inicial = %s
             WHERE id_usuario = %s
               AND id_cuenta = %s
            """,
            (nombre, str(tipo), saldo_inicial, id_usuario, id_cuenta),
        )

    def cambiar_activa(self, id_usuario: int, id_cuenta: int, activa: bool) -> None:
        """Archivar (False) o reactivar (True). Nunca se borra la fila (RN-12, RNF-05)."""
        self.con.execute(
            "UPDATE cuenta SET activa = %s WHERE id_usuario = %s AND id_cuenta = %s",
            (activa, id_usuario, id_cuenta),
        )
