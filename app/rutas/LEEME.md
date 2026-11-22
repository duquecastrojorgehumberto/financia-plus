# app/rutas/

**Estado:** `salud.py` y `autenticacion.py` hechos. Los demás módulos están pendientes.

Un archivo por módulo (`cuentas.py`, `movimientos.py`...), cada uno con un *blueprint* de
Flask bajo `/api/`. Cada ruta: exige sesión, lee y valida la **forma** de los datos JSON,
llama a **un** método de servicio y responde JSON.

| Archivo | Rutas |
| --- | --- |
| `salud.py` | `GET /api/salud`: `{"bd": "ok"}` (200) o `{"bd": "error"}` (503). |
| `autenticacion.py` | `POST /api/registro`; `POST`, `GET` y `DELETE /api/sesion` (RF-01). |
| `entrada.py` | `leer_textos(...)`: comprueba que el cuerpo JSON traiga los campos de texto pedidos. |

No va aquí: reglas de negocio, SQL ni transacciones.
