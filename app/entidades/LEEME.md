# app/entidades/

Clases de datos (`@dataclass(frozen=True)`), una por tabla, y las enumeraciones de los
valores fijos (`TipoMovimiento`, `TipoCuenta`...). No acceden a la base.
Ver `docs/ARQUITECTURA.md`, sección 3.1.

| Archivo | Contenido | Estado |
| --- | --- | --- |
| `usuario.py` | `Usuario`; `datos_publicos()` devuelve lo que se puede enviar al navegador (sin `clave_hash`). | Hecho (Tarea 7) |
| `categoria.py` | `Categoria` con `es_subcategoria()` y `datos_publicos()`, `TipoCategoria` (`StrEnum`: INGRESO, EGRESO) y `RamaCategoria` (una raíz + sus subcategorías, por composición). | Hecho (Tareas 7 y 9) |
| `cuenta.py` | `Cuenta` (la fila), `TipoCuenta` (`StrEnum`) y `CuentaConSaldo` (una `Cuenta` + su saldo calculado, por composición), con `saldo_negativo()` y `datos_publicos()`. | Hecho (Tarea 8) |
| `movimiento.py` | `Movimiento` (una sola clase para los cinco tipos, D-03), `TipoMovimiento`, `EstadoMovimiento` y `MovimientoDetalle` (movimiento + nombres de cuenta y categoría, por composición) y `TransferenciaConCargos` (una transferencia y sus cargos). | Hecho (Tareas 10 y 11) |
| `bolsillo.py` | `Bolsillo` (con `es_meta()`), `ValorBolsillo` (una fila del historial) y `BolsilloConValor` (bolsillo + valor actual, por composición; `progreso_porcentaje()`). | Hecho (Tarea 13) |
