# app/ — Aplicación

**Estado: vacío. Nada implementado.**

Aquí va la aplicación Flask, en tres capas. Qué hace cada una está en
`docs/ARQUITECTURA.md`, sección 3.

| Carpeta | Contenido |
| --- | --- |
| `rutas/` | Un archivo por módulo. Reciben la petición y llaman a un servicio. |
| `servicios/` | Un archivo por módulo. Reglas de negocio y transacciones. |
| `repositorios/` | Un archivo por módulo. SQL parametrizado. |
| `entidades/` | Clases de datos (`dataclasses`), una por tabla. |

Archivos previstos en esta carpeta (Tarea 6 de la guía): `__init__.py` (fábrica de la
aplicación), `config.py` (lee variables de entorno), `bd.py` (conexión y transacciones).

Módulos: `autenticacion`, `cuentas`, `categorias`, `movimientos`, `transferencias`,
`bolsillos`, `resumen`.
