# app/servicios/

Una clase por módulo. Aquí viven las reglas de `docs/REGLAS_NEGOCIO.md` marcadas como
"Servicio". Regla de oro: **una acción del usuario = un método = una transacción**
(`with self.con.transaction():`).

| Archivo | Contenido | Estado |
| --- | --- | --- |
| `autenticacion.py` | `AutenticacionServicio`: `registrar` (usuario + categorías en una transacción), `iniciar_sesion`, `obtener_usuario_activo` | Hecho (Tarea 7) |
| `categorias_por_defecto.py` | La lista de categorías que recibe cada usuario nuevo (RN-26) | Hecho (Tarea 7) |
| `categorias.py` | `CategoriaServicio`: `listar_arbol` (con filtros), `obtener`, `crear` (raíz o subcategoría, máximo dos niveles), `renombrar` (solo el nombre, RN-22), `desactivar` (con sus subcategorías), `reactivar` | Hecho (Tarea 9) |
| `cuentas.py` | `CuentaServicio`: `listar`, `obtener`, `crear`, `editar` (RN-13), `archivar` (solo con saldo 0, bloqueando la fila), `reactivar` | Hecho (Tarea 8) |

Operaciones que exigen transacción explícita:
- Registro de usuario con sus categorías por defecto (RN-26). **Hecho.**
- Transferencia con sus cargos (RN-37) y su anulación (RN-38).
- Crear bolsillo con su primer valor (RN-45).
- Ajuste de saldo, bloqueando la fila de la cuenta (RN-55).
- Archivar una cuenta, bloqueando su fila mientras se revisa que el saldo sea 0 (RN-12, D-20). **Hecho.**
- Desactivar una categoría raíz junto con sus subcategorías (RN-25). **Hecho.**

No va aquí: objetos de Flask (request, session), JSON ni SQL.
