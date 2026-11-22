# db/migraciones/

**Estado: `0001` y `0002` aplicadas en `financia` y `financia_pruebas` y probadas.**

## Convención

- Nombre: `NNNN_descripcion.sql` (`0001_esquema_inicial.sql`, `0002_roles_y_permisos.sql`...).
- Se aplican en orden con `scripts/migrar.py`, que anota cada una en la tabla de
  control `migracion_aplicada`.
- Cada archivo va dentro de `BEGIN; ... COMMIT;`.
- **Una migración aplicada no se edita.** Un cambio va en un archivo nuevo.
- Sin instrucciones destructivas (`DROP DATABASE`, borrados masivos).

## Migraciones previstas

| Archivo | Contenido | Especificación |
| --- | --- | --- |
| `0001_esquema_inicial.sql` | Las 6 tablas con restricciones e índices. **Aplicada** | `docs/MODELO_DATOS.md`, sección 4 |
| `0002_roles_y_permisos.sql` | Permisos del rol `financia_app` (sin DELETE; solo SELECT e INSERT en `bolsillo_valor`). No crea el rol: lo crea `scripts/preparar_bd.py`. **Aplicada** | `docs/DECISIONES_ARQUITECTURA.md`, D-15 |

Las funcionalidades aplazadas llegarán como migraciones posteriores.
