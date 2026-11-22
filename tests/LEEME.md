# tests/

**Estado: todas las pruebas de esta carpeta se ejecutan y pasan.**

Pruebas con `pytest` contra una base PostgreSQL de pruebas (`DATABASE_URL_PRUEBAS`).

| Archivo | Qué prueba | Estado |
| --- | --- | --- |
| `conftest.py` | Conexiones a la base de pruebas: `con` (rol dueño) y `con_app` (rol `financia_app`). Cada prueba termina en ROLLBACK | Funciona |
| `test_restricciones_bd.py` | Que la base rechaza lo que debe rechazar y acepta lo que debe aceptar (Tarea 5) | Pasa |
| `test_permisos_bd.py` | Que `financia_app` no puede borrar ni modificar el historial de bolsillos (Tarea 4, D-15) | Pasa |
| `test_cuentas.py`, `test_movimientos.py`, `test_transferencias.py`, `test_bolsillos.py`, `test_resumen.py` | Servicios y criterios CA-01 a CA-15 | Pendiente |

## Cómo ejecutarlas

Desde la carpeta del proyecto:

```powershell
.venv\Scripts\python -m pytest tests -q
```

Requisitos: la base de pruebas con todas las migraciones aplicadas
(`.venv\Scripts\python scripts\migrar.py --variable DATABASE_URL_PRUEBAS`) y el archivo
`.env` con `DATABASE_URL_PRUEBAS` y `DATABASE_URL`. Sin esas variables, las pruebas se
omiten en lugar de fallar.

## Convenciones

- Cada prueba cita lo que verifica (RN-xx, CA-xx, D-xx o la sección de `MODELO_DATOS.md`).
- Cada rechazo comprueba el tipo de error **y el nombre de la restricción** que lo produjo.
- Cada caso parte de una fila válida y cambia una sola cosa.
- Las pruebas llamadas `test_limite_conocido_...` documentan lo que la base **no** garantiza
  y debe garantizar la capa de servicios.
- Ninguna prueba deja datos en la base.
