# app/servicios/

**Estado: vacío.**

Un archivo por módulo. Aquí viven las reglas de `docs/REGLAS_NEGOCIO.md` marcadas como
"Servicio". Regla de oro: **una acción del usuario = una función = una transacción.**

Operaciones que exigen transacción explícita:
- Transferencia con sus cargos (RN-37) y su anulación (RN-38).
- Crear bolsillo con su primer valor (RN-45).
- Ajuste de saldo, bloqueando la fila de la cuenta (RN-55).
- Registro de usuario con sus categorías por defecto (RN-26).

No va aquí: HTML, objetos de Flask ni SQL.
