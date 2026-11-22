# app/servicios/

Una clase por módulo. Aquí viven las reglas de `docs/REGLAS_NEGOCIO.md` marcadas como
"Servicio". Regla de oro: **una acción del usuario = un método = una transacción**
(`with self.con.transaction():`).

| Archivo | Contenido | Estado |
| --- | --- | --- |
| `autenticacion.py` | `AutenticacionServicio`: `registrar` (usuario + categorías en una transacción), `iniciar_sesion`, `obtener_usuario_activo` | Hecho (Tarea 7) |
| `categorias_por_defecto.py` | La lista de categorías que recibe cada usuario nuevo (RN-26) | Hecho (Tarea 7) |
| `categorias.py` | `CategoriaServicio`: `listar_arbol` (con filtros), `obtener`, `crear` (raíz o subcategoría, máximo dos niveles), `renombrar` (solo el nombre, RN-22), `desactivar` (con sus subcategorías), `reactivar` | Hecho (Tarea 9) |
| `movimientos.py` | `MovimientoServicio`: `historial` (filtros), `obtener`, `registrar` (ingreso o egreso), `corregir` (RN-72), `anular`, `reactivar`. `DatosMovimiento` y `FiltroHistorial` agrupan los datos de entrada | Hecho (Tarea 10) |
| `transferencias.py` | `TransferenciaServicio`: `registrar` (transferencia + cargos en una transacción), `obtener`, `corregir`, `agregar_cargo`, `corregir_cargo`, `anular` (en cascada), `reactivar` | Hecho (Tarea 11) |
| `ajustes.py` | `AjusteServicio`: `ajustar` (saldo real → ajuste por la diferencia, bloqueando la cuenta), `corregir` (fecha y motivo). `ResultadoAjuste` | Hecho (Tarea 12) |
| `bolsillos.py` | `BolsilloServicio`: `listar`, `obtener`, `historial`, `crear` (con su primer valor, RN-45), `editar`, `cambiar_valor` (RN-44, RN-46), `archivar`, `reactivar` | Hecho (Tarea 13) |
| `resumen.py` | `ResumenServicio`: `indicadores` (RN-60 a RN-63) y `periodo` (RN-64, RN-53, RN-27). `Indicadores`, `ResumenPeriodo`, `TotalCategoria` | Hecho (Tarea 14) |
| `verificaciones.py` | `VerificadorDeUso`: cuenta activa y categoría utilizable, con `FOR SHARE`. Lo contienen `MovimientoServicio` y `TransferenciaServicio` (composición, sin copiar código) | Hecho (Tarea 11) |
| `validaciones.py` | `validar_dinero`: monto o saldo con máximo 2 decimales y dentro de `numeric(14,2)` | Hecho (Tarea 10) |
| `cuentas.py` | `CuentaServicio`: `listar`, `obtener`, `crear`, `editar` (RN-13), `archivar` (solo con saldo 0, bloqueando la fila), `reactivar` | Hecho (Tarea 8) |

Operaciones que exigen transacción explícita:
- Registro de usuario con sus categorías por defecto (RN-26). **Hecho.**
- Transferencia con sus cargos (RN-37) y su anulación (RN-38). **Hecho.**
- Crear bolsillo con su primer valor (RN-45). **Hecho.**
- Ajuste de saldo, bloqueando la fila de la cuenta (RN-55). **Hecho.**
- Archivar una cuenta, bloqueando su fila mientras se revisa que el saldo sea 0 (RN-12, D-20). **Hecho.**
- Desactivar una categoría raíz junto con sus subcategorías (RN-25). **Hecho.**

No va aquí: objetos de Flask (request, session), JSON ni SQL.
