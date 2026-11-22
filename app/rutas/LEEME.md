# app/rutas/

**Estado:** `salud.py`, `autenticacion.py`, `cuentas.py`, `categorias.py`, `movimientos.py`, `transferencias.py` y `ajustes.py` hechos. Los demás módulos están pendientes.

Un archivo por módulo (`cuentas.py`, `movimientos.py`...), cada uno con un *blueprint* de
Flask bajo `/api/`. Cada ruta: exige sesión, lee y valida la **forma** de los datos JSON,
llama a **un** método de servicio y responde JSON.

| Archivo | Rutas |
| --- | --- |
| `salud.py` | `GET /api/salud`: `{"bd": "ok"}` (200) o `{"bd": "error"}` (503). |
| `autenticacion.py` | `POST /api/registro`; `POST`, `GET` y `DELETE /api/sesion` (RF-01). |
| `cuentas.py` | `GET`/`POST /api/cuentas`; `GET`/`PUT /api/cuentas/<id>`; `POST /api/cuentas/<id>/archivar` y `/reactivar` (RF-02, RF-11). |
| `categorias.py` | `GET`/`POST /api/categorias` (`?tipo=` e `?inactivas=1`); `GET`/`PUT /api/categorias/<id>`; `POST /api/categorias/<id>/desactivar` y `/reactivar` (RF-03). |
| `movimientos.py` | `GET`/`POST /api/movimientos` (historial con filtros `desde`, `hasta`, `id_cuenta`, `tipo`, `id_categoria`, `estado`); `GET`/`PUT /api/movimientos/<id>`; `POST …/anular` y `…/reactivar` (RF-04, RF-05, RF-14, RF-16). |
| `transferencias.py` | `POST /api/transferencias` (con `cargos`); `GET`/`PUT /api/transferencias/<id>`; `POST …/anular` y `…/reactivar`; `POST …/cargos` y `PUT …/cargos/<id_cargo>` (RF-06, RF-07). |
| `ajustes.py` | `POST /api/cuentas/<id>/ajustes` (saldo real y motivo); `PUT /api/ajustes/<id>` (fecha y motivo) (RF-17). |
| `entrada.py` | `fecha_opcional`, `lista_de_objetos`, `leer_cuerpo`, `texto`, `texto_opcional`, `dinero`, `entero`, `entero_opcional`, `fecha`, `solo_campos` y los `parametro_*` de la URL: comprueban la forma del JSON. El dinero llega como texto (`"150000.50"`), nunca como número. |

No va aquí: reglas de negocio, SQL ni transacciones.
