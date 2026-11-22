# tests/

**Estado: `test_restricciones_bd.py` y `conftest.py` están escritos y revisados a mano.
Todavía no se han ejecutado.** No hay más pruebas.

Pruebas con `pytest` contra una base PostgreSQL de pruebas (`DATABASE_URL_PRUEBAS`).

| Archivo | Qué prueba | Estado |
| --- | --- | --- |
| `conftest.py` | Conexión a la base de pruebas; cada prueba termina en ROLLBACK | Escrito, sin ejecutar |
| `test_restricciones_bd.py` | Que la base rechaza lo que debe rechazar y acepta lo que debe aceptar (Tarea 5) | Escrito, sin ejecutar |
| `test_cuentas.py`, `test_movimientos.py`, `test_transferencias.py`, `test_bolsillos.py`, `test_resumen.py` | Servicios y criterios CA-01 a CA-15 | Pendiente |

## Cómo ejecutarlas (cuando el entorno esté listo)

1. Crear una base de pruebas vacía y aplicarle `db/migraciones/0001_esquema_inicial.sql`.
2. Definir `DATABASE_URL_PRUEBAS` con un rol dueño de las tablas.
3. `pytest tests/test_restricciones_bd.py -v`

Sin `DATABASE_URL_PRUEBAS`, las pruebas se omiten en lugar de fallar.

## Convenciones

- Cada prueba cita lo que verifica (RN-xx, CA-xx, D-xx o la sección de `MODELO_DATOS.md`).
- Cada rechazo comprueba el tipo de error **y el nombre de la restricción** que lo produjo.
- Cada caso parte de una fila válida y cambia una sola cosa.
- Las pruebas llamadas `test_limite_conocido_...` documentan lo que la base **no** garantiza
  y debe garantizar la capa de servicios.
- Ninguna prueba deja datos en la base.
