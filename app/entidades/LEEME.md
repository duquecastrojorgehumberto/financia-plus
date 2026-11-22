# app/entidades/

Clases de datos (`@dataclass(frozen=True)`), una por tabla, y las enumeraciones de los
valores fijos (`TipoMovimiento`, `TipoCuenta`...). No acceden a la base.
Ver `docs/ARQUITECTURA.md`, sección 3.1.

| Archivo | Contenido | Estado |
| --- | --- | --- |
| `usuario.py` | `Usuario`; `datos_publicos()` devuelve lo que se puede enviar al navegador (sin `clave_hash`). | Hecho (Tarea 7) |
| `categoria.py` | `Categoria` con `es_subcategoria()`, y `TipoCategoria` (`StrEnum`: INGRESO, EGRESO). | Hecho (Tarea 7) |
| `cuenta.py`, `movimiento.py`, `bolsillo.py`... | Resto de tablas. | Pendiente |
