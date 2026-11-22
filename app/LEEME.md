# app/ — Aplicación

**Estado: esqueleto funcionando (Tarea 6). Sin módulos de negocio todavía.**

Aquí va la aplicación Flask, en tres capas. Qué hace cada una está en
`docs/ARQUITECTURA.md`, sección 3.

| Carpeta | Contenido |
| --- | --- |
| `rutas/` | Un archivo por módulo. Reciben la petición y llaman a un servicio. |
| `servicios/` | Un archivo por módulo. Reglas de negocio y transacciones. |
| `repositorios/` | Un archivo por módulo. SQL parametrizado. |
| `entidades/` | Clases de datos (`dataclasses`), una por tabla. |

Archivos de esta carpeta (Tarea 6):

| Archivo | Qué hace |
| --- | --- |
| `__init__.py` | `create_app()`: la fábrica que arma la aplicación (configuración, base, CSRF, errores, rutas). |
| `config.py` | Clase `Config`: lee `SECRET_KEY` y `DATABASE_URL` del entorno. |
| `bd.py` | Clase `BaseDatos` y una conexión por petición. Las transacciones: `with con.transaction():`. |
| `errores.py` | `ErrorNegocio` (400) y `NoEncontrado` (404), convertidos a JSON. |
| `csrf.py` | Rechaza las peticiones que modifican datos sin JSON o sin `X-Requested-With: financia`. |

Módulos: `autenticacion`, `cuentas`, `categorias`, `movimientos`, `transferencias`,
`bolsillos`, `resumen`.
