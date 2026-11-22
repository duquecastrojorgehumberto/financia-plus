# app/rutas/

**Estado:** solo `salud.py` (`GET /api/salud`). Los módulos de negocio están pendientes.

Un archivo por módulo (`cuentas.py`, `movimientos.py`...), cada uno con un *blueprint* de
Flask bajo `/api/`. Cada ruta: exige sesión, lee y valida la **forma** de los datos JSON,
llama a **un** método de servicio y responde JSON.

| Archivo | Rutas |
| --- | --- |
| `salud.py` | `GET /api/salud`: `{"bd": "ok"}` (200) o `{"bd": "error"}` (503). |

No va aquí: reglas de negocio, SQL ni transacciones.
