# app/repositorios/

Una clase por tabla (`UsuarioRepositorio`, `CategoriaRepositorio`...). Recibe la conexión en
el constructor; cada método ejecuta una consulta SQL escrita a mano y devuelve entidades.

| Archivo | Clase | Estado |
| --- | --- | --- |
| `usuarios.py` | `UsuarioRepositorio`: `insertar`, `obtener`, `obtener_por_correo` | Hecho (Tarea 7) |
| `categorias.py` | `CategoriaRepositorio`: `listar`, `obtener`, `obtener_para_actualizar` (`FOR UPDATE`), `obtener_para_usar` (`FOR SHARE`), `insertar`, `renombrar`, `cambiar_activa`, `desactivar_subcategorias` | Hecho (Tareas 7 y 9) |
| `cuentas.py` | `CuentaRepositorio`: la consulta del **saldo calculado**, `obtener_para_actualizar` (`FOR UPDATE`), `obtener_para_usar` (`FOR SHARE`), `tiene_movimientos`, `insertar`, `actualizar`, `cambiar_activa` | Hecho (Tarea 8) |

Reglas:
- Todo método recibe `id_usuario` y lo usa en el `WHERE`. Única excepción:
  `UsuarioRepositorio.obtener_por_correo`, porque al iniciar sesión todavía no se conoce.
- Siempre parámetros (`%s`). Nunca f-strings ni concatenación para armar SQL.
- No hacen COMMIT ni ROLLBACK: eso lo decide el servicio.
- Dinero como `Decimal`.

| Archivo (Tarea 10) | Clase | Estado |
| --- | --- | --- |
| `movimientos.py` | `MovimientoRepositorio`: `listar` (historial con filtros opcionales en una sola consulta), `obtener_detalle`, `obtener_para_actualizar`, `insertar_ingreso_o_egreso`, `corregir`, `cambiar_estado`; para transferencias: `listar_cargos`, `bloquear_cargos`, `insertar_transferencia`, `insertar_cargo`, `corregir_transferencia`, `cambiar_fecha_cargos`, `corregir_cargo`; para ajustes: `insertar_ajuste`, `corregir_ajuste` | Hecho (Tareas 10 a 12) |

Bloqueos que usan los repositorios:
- `FOR UPDATE` (exclusivo): la fila que se va a cambiar. Nadie más la cambia ni la usa hasta el COMMIT.
- `FOR SHARE` (compartido): la cuenta o categoría que un movimiento va a usar. Varias transacciones
  pueden tenerlo a la vez, pero archivar la cuenta o desactivar la categoría tiene que esperar.

| Archivo (Tarea 13) | Clase | Estado |
| --- | --- | --- |
| `bolsillos.py` | `BolsilloRepositorio`: `listar_con_valor` (valor actual con `DISTINCT ON`), `obtener_con_valor`, `historial`, `obtener_para_actualizar`, `insertar`, `insertar_valor` (solo inserta: el historial no se modifica), `actualizar`, `cambiar_activo` | Hecho (Tarea 13) |

| Archivo (Tarea 14) | Clase | Estado |
| --- | --- | --- |
| `resumen.py` | `ResumenRepositorio` (solo lectura): `totales_por_tipo` y `totales_por_categoria` del periodo. El saldo total y el total reservado reutilizan `CuentaRepositorio` y `BolsilloRepositorio` | Hecho (Tarea 14) |
