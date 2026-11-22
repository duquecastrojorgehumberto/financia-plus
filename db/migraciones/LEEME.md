# db/migraciones/

**Estado: `0001_esquema_inicial.sql` está escrito y revisado a mano. Todavía no se ha ejecutado.**

## Convención

- Nombre: `NNNN_descripcion.sql` (`0001_esquema_inicial.sql`, `0002_roles_permisos.sql`...).
- Se aplican en orden con `scripts/migrar.py` (pendiente), que anota cada una en la tabla de
  control `migracion_aplicada`.
- Cada archivo va dentro de `BEGIN; ... COMMIT;`.
- **Una migración aplicada no se edita.** Un cambio va en un archivo nuevo.
- Sin instrucciones destructivas (`DROP DATABASE`, borrados masivos).

## Migraciones previstas

| Archivo | Contenido | Especificación |
| --- | --- | --- |
| `0001_esquema_inicial.sql` | Las 6 tablas con restricciones e índices. **Escrito, sin ejecutar** | `docs/MODELO_DATOS.md`, sección 4 |
| `0002_roles_permisos.sql` | Permisos del rol de la aplicación (sin DELETE). **Pendiente** | `docs/DECISIONES_ARQUITECTURA.md`, D-15 |

Las funcionalidades aplazadas llegarán como migraciones posteriores.
