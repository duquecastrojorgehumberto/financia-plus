# tests/

**Estado: todas las pruebas de esta carpeta se ejecutan y pasan.**

Pruebas con `pytest` contra una base PostgreSQL de pruebas (`DATABASE_URL_PRUEBAS`).

| Archivo | Qué prueba | Estado |
| --- | --- | --- |
| `conftest.py` | Conexiones a la base de pruebas: `con` (rol dueño), `con_app` (rol `financia_app`), `con_tx` y `cliente_api` (servicios y API: lo que confirman se deshace al final con ROLLBACK), `cuenta_confirmada` (datos confirmados para probar bloqueos entre dos conexiones) y `Mundo` (un usuario con dos cuentas y sus categorías) | Funciona |
| `test_restricciones_bd.py` | Que la base rechaza lo que debe rechazar y acepta lo que debe aceptar (Tarea 5) | Pasa |
| `test_permisos_bd.py` | Que `financia_app` no puede borrar ni modificar el historial de bolsillos (Tarea 4, D-15) | Pasa |
| `test_api_base.py` | `/api/salud`, protección CSRF y errores en JSON (Tarea 6) | Pasa |
| `test_autenticacion.py` | Registro, inicio y cierre de sesión (Tarea 7) | Pasa |
| `test_cuentas.py` | Saldo calculado, crear, editar, archivar con saldo 0 y bloqueo de la fila (Tarea 8) | Pasa |
| `test_categorias.py` | Raíces y subcategorías, dos niveles, solo cambia el nombre, desactivar con subcategorías, CA-14 (Tarea 9) | Pasa |
| `test_movimientos.py` | Ingresos y egresos, CA-01, CA-05, CA-06, CA-13, CA-14, corregir, anular, reactivar, historial con filtros y carreras reales entre dos conexiones (Tarea 10) | Pasa |
| `test_transferencias.py` | CA-02, CA-03 (con regla rota y con falla técnica), CA-04, corregir transferencia y cargos, agregar cargos, reactivar (Tarea 11) | Pasa |
| `test_ajustes.py` | CA-11, aumento, sin diferencia, saldo negativo, corregir, anular y carrera real de RN-55 (Tarea 12) | Pasa |
| `test_bolsillos.py` | CA-07, CA-08, CA-09, primer valor en la misma transacción, valor igual sin registro, desempate del más reciente, metas, archivar (Tarea 13) | Pasa |
| `test_datos_prueba.py` | Carga `db/semillas/datos_prueba.sql` (y lo deshace) y comprueba cada resultado que promete; los rechazos sobre esos datos (Tarea 15) | Pasa |
| `test_resumen.py` | Indicadores, CA-10, CA-12 y, vistos desde el resumen, CA-01, CA-02, CA-11 y CA-14 (Tarea 14) | Pasa |

## Criterios de aceptación y dónde se prueban

| Criterio | Qué comprueba | Pruebas |
| --- | --- | --- |
| CA-01 | Saldo 100.000 + 50.000 − 20.000 = 130.000 | `test_cuentas`, `test_movimientos`, `test_resumen`, `test_datos_prueba` |
| CA-02 | Transferencia con cargo de 800 | `test_transferencias`, `test_resumen`, `test_datos_prueba` |
| CA-03 | Cargo inválido: no queda nada | `test_transferencias` (con prueba de mutación), `test_datos_prueba` |
| CA-04 | Anular la transferencia y su cargo | `test_transferencias`, `test_datos_prueba` |
| CA-05 | Egreso con categoría de ingreso | `test_restricciones_bd` (base), `test_movimientos` (servicio), `test_datos_prueba` |
| CA-06 | Datos de otro usuario | `test_restricciones_bd` (base), `test_movimientos`, `test_transferencias`, `test_datos_prueba` |
| CA-07 | Meta al 35 % sin tocar cuentas | `test_bolsillos`, `test_datos_prueba` |
| CA-08 | Valor −1 en un bolsillo | `test_restricciones_bd` (base), `test_bolsillos`, `test_datos_prueba` |
| CA-09 | Transferencia no cambia un bolsillo | `test_bolsillos`, `test_datos_prueba` |
| CA-10 | Disponible −50.000 con aviso | `test_resumen`, `test_datos_prueba` |
| CA-11 | Ajuste de 6.500 sin cambiar egresos | `test_ajustes`, `test_resumen`, `test_datos_prueba` |
| CA-12 | Alimentación 50.000 con Mercado 30.000 | `test_resumen`, `test_datos_prueba` |
| CA-13 | Egreso anulado visible en el historial | `test_movimientos`, `test_datos_prueba` |
| CA-14 | Categoría desactivada con movimientos | `test_categorias`, `test_movimientos`, `test_resumen`, `test_datos_prueba` |
| CA-15 | Archivar solo con saldo 0 | `test_cuentas`, `test_datos_prueba` |

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
