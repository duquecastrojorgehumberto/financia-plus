# app/repositorios/

Una clase por tabla (`UsuarioRepositorio`, `CategoriaRepositorio`...). Recibe la conexión en
el constructor; cada método ejecuta una consulta SQL escrita a mano y devuelve entidades.

| Archivo | Clase | Estado |
| --- | --- | --- |
| `usuarios.py` | `UsuarioRepositorio`: `insertar`, `obtener`, `obtener_por_correo` | Hecho (Tarea 7) |
| `categorias.py` | `CategoriaRepositorio`: `insertar`, `listar` | Hecho (Tarea 7); se amplía en la Tarea 9 |

Reglas:
- Todo método recibe `id_usuario` y lo usa en el `WHERE`. Única excepción:
  `UsuarioRepositorio.obtener_por_correo`, porque al iniciar sesión todavía no se conoce.
- Siempre parámetros (`%s`). Nunca f-strings ni concatenación para armar SQL.
- No hacen COMMIT ni ROLLBACK: eso lo decide el servicio.
- Dinero como `Decimal`.
