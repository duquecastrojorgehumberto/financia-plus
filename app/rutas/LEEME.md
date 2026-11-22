# app/rutas/

**Estado:** `salud.py`, `autenticacion.py`, `cuentas.py` y `categorias.py` hechos. Los demás módulos están pendientes.

Un archivo por módulo (`cuentas.py`, `movimientos.py`...), cada uno con un *blueprint* de
Flask bajo `/api/`. Cada ruta: exige sesión, lee y valida la **forma** de los datos JSON,
llama a **un** método de servicio y responde JSON.

| Archivo | Rutas |
| --- | --- |
| `salud.py` | `GET /api/salud`: `{"bd": "ok"}` (200) o `{"bd": "error"}` (503). |
| `autenticacion.py` | `POST /api/registro`; `POST`, `GET` y `DELETE /api/sesion` (RF-01). |
| `cuentas.py` | `GET`/`POST /api/cuentas`; `GET`/`PUT /api/cuentas/<id>`; `POST /api/cuentas/<id>/archivar` y `/reactivar` (RF-02, RF-11). |
| `categorias.py` | `GET`/`POST /api/categorias` (`?tipo=` e `?inactivas=1`); `GET`/`PUT /api/categorias/<id>`; `POST /api/categorias/<id>/desactivar` y `/reactivar` (RF-03). |
| `entrada.py` | `leer_cuerpo`, `texto`, `dinero`, `entero_opcional` y `solo_campos`: comprueban la forma del JSON. El dinero llega como texto (`"150000.50"`), nunca como número. |

No va aquí: reglas de negocio, SQL ni transacciones.
