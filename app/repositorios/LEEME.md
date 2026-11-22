# app/repositorios/

**Estado: vacío.**

Un archivo por módulo. Cada función ejecuta una consulta SQL escrita a mano.

Reglas:
- Toda función recibe `id_usuario` y lo usa en el `WHERE`.
- Siempre parámetros (`%s`). Nunca f-strings ni concatenación para armar SQL.
- No hacen COMMIT ni ROLLBACK: eso lo decide el servicio.
- Dinero como `Decimal`.
