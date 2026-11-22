# Decisiones de arquitectura — FINANCIA+ versión 1

Cada decisión dice qué se decidió, por qué, qué alternativa se descartó y qué consecuencia
trae. **Todas las decisiones están confirmadas por el estudiante (17 de noviembre de 2026).** Las que
nacieron como propuesta llevan la nota "Confirmada". Ya no hay decisiones abiertas.

## Índice

| # | Decisión | Estado |
| --- | --- | --- |
| D-01 | Seis tablas; nada para funcionalidades futuras | Tomada |
| D-02 | Propiedad con claves foráneas compuestas | Tomada |
| D-03 | Un solo `movimiento` con cinco tipos | Tomada |
| D-04 | La transferencia es una sola fila | Tomada |
| D-05 | El cargo de una transferencia es un EGRESO enlazado | Tomada |
| D-06 | Una sola categoría por movimiento | Tomada |
| D-07 | Tipo de categoría = tipo de movimiento, con una FK | Tomada |
| D-08 | Meta = bolsillo con monto objetivo (sin tabla de metas) | Tomada |
| D-09 | Valor del bolsillo: historial; el último registro es el valor actual | Tomada |
| D-10 | Bolsillos sin relación con cuentas ni movimientos | Tomada |
| D-11 | Saldos y demás datos derivados se calculan | Tomada |
| D-12 | Ajuste de saldo como movimiento propio, calculado por el sistema | Confirmada |
| D-13 | Categorías de dos niveles y padre inmutable | Confirmada |
| D-14 | Cero triggers; reglas de varios pasos en servicios con transacción | Tomada |
| D-15 | Borrado lógico reforzado con permisos del rol | Confirmada |
| D-16 | Tipo de cuenta como CHECK, sin tabla de catálogo | Confirmada |
| D-17 | Correcciones en sitio, sin historial de versiones | Confirmada |
| D-18 | Flask como API JSON + psycopg + SQL a mano | Confirmada (cambiada el 21/11/2026) |
| D-19 | Migraciones: archivos SQL numerados y un script propio | Confirmada |
| D-20 | Una cuenta solo se archiva con saldo 0; un bolsillo se archiva con cualquier valor | Tomada |
| D-21 | POO por capas e interfaz React + Vite + TypeScript separada | Confirmada |

---

## D-01. Seis tablas; nada para funcionalidades futuras
**Decisión.** `usuario`, `cuenta`, `categoria`, `movimiento`, `bolsillo`, `bolsillo_valor`.
**Por qué.** El enunciado prohíbe tablas vacías "por si acaso". Cada tabla responde a un requisito de la versión 1.
**Descartado.** Conservar las 26 tablas del diseño anterior, o dejar creadas las de facturas y Gmail.
**Consecuencia.** Lo aplazado llegará con migraciones nuevas. No se necesitan tablas de preferencias (no hay alertas configurables) ni de catálogos.

## D-02. Propiedad con claves foráneas compuestas
**Decisión.** Toda tabla hija lleva `id_usuario`, declara `UNIQUE (id_usuario, id_x)` y las FK apuntan a esa pareja.
**Por qué.** Es la única forma **declarativa** de impedir que un registro de un usuario se enlace con uno de otro. Con una FK simple (`id_cuenta`), un error del backend podría guardar un movimiento de U1 en una cuenta de U2 y la base lo aceptaría.
**Descartado.** Confiar solo en el filtro del backend; usar triggers de validación.
**Consecuencia.** `id_usuario` se repite en las tablas hijas (redundancia controlada: la FK garantiza que coincide). Es lo más valioso que se conserva del diseño anterior.

## D-03. Un solo `movimiento` con cinco tipos
**Decisión.** INGRESO, EGRESO, TRANSFERENCIA, AJUSTE_AUMENTO y AJUSTE_DISMINUCION viven en una tabla, con la columna `tipo` y un CHECK que indica qué columnas usa cada uno.
**Por qué.** El historial y el saldo de una cuenta salen de una sola consulta. Los cinco tipos comparten casi todas sus columnas.
**Descartado.** Una tabla por tipo (obliga a `UNION` en cada consulta de saldo e historial).
**Consecuencia.** Tres columnas admiten NULL según el tipo; el CHECK de forma evita combinaciones inválidas.

## D-04. La transferencia es una sola fila
**Decisión.** Una transferencia es una fila con `id_cuenta` (origen) e `id_cuenta_destino`.
**Por qué.** El enunciado exige que nunca quede registrada solo una de sus dos partes. Con una fila, eso es **imposible por construcción**: no hay dos partes que guardar.
**Descartado.** Dos filas enlazadas (una salida y una entrada): exige transacción, un identificador de pareja y validar que los montos coincidan.
**Consecuencia.** El saldo de una cuenta debe mirar dos columnas (origen y destino).

## D-05. El cargo de una transferencia es un EGRESO enlazado
**Decisión.** Cada cargo (4×1.000, comisión) es una fila EGRESO normal, con su categoría, y la columna `id_transferencia` apunta a la transferencia. La FK incluye `id_cuenta`, de modo que el cargo sale obligatoriamente de la cuenta de origen.
**Por qué.** El enunciado pide que el cargo "se contabilice como un egreso independiente" con trazabilidad. Al ser un EGRESO de verdad, aparece solo en saldos, historial y totales por categoría, sin consultas especiales.
**Descartado.**
- Columnas `cargo_monto` y `cargo_categoria` dentro de la transferencia: sería una sola fila, pero todo reporte de gastos tendría que acordarse de sumar esas columnas. Es la clase de detalle que se olvida y produce totales errados. Además limita a un cargo por transferencia.
- Tabla aparte `cargo_transferencia`: una tabla más para guardar lo mismo que ya sabe guardar `movimiento`.
**Consecuencia.** Son dos o más filas, así que la atomicidad depende de una transacción en el servicio (RN-37). Se admiten varios cargos por transferencia.

## D-06. Una sola categoría por movimiento
**Decisión.** `movimiento.id_categoria`; sin tabla de líneas.
**Por qué.** Lo fija el enunciado. Es lo más simple de registrar y de explicar.
**Descartado.** `movimiento_linea` del diseño anterior.
**Consecuencia.** Una compra mixta se registra como dos egresos. La evolución a líneas es una migración sin pérdida de datos (`MODELO_DATOS.md`, sección 7).

## D-07. Tipo de categoría = tipo de movimiento, con una FK
**Decisión.** `FOREIGN KEY (id_usuario, id_categoria, tipo) REFERENCES categoria (id_usuario, id_categoria, tipo)`.
**Por qué.** La columna `tipo` del movimiento participa en la FK; si el movimiento es EGRESO, solo encuentra pareja en una categoría EGRESO. Regla cumplida sin trigger.
**Descartado.** Trigger de validación; validar solo en el backend.
**Consecuencia.** `categoria` necesita la superclave `UNIQUE (id_usuario, id_categoria, tipo)`. En transferencias y ajustes `id_categoria` es NULL y la FK no se evalúa.

## D-08. Meta = bolsillo con monto objetivo
**Decisión.** No hay tabla de metas. Un bolsillo es "con meta" cuando `monto_objetivo` tiene valor.
**Por qué.** La meta no tiene vida propia: solo agrega dos atributos opcionales (monto y fecha objetivo) a un bolsillo. Una tabla aparte obligaría a una relación 1 a 1 y a un JOIN para cada pantalla, sin ganar nada.
**Descartado.** Tabla `meta_ahorro` (diseño anterior); columna `modalidad` (sería un dato derivable que podría contradecir a `monto_objetivo`).
**Consecuencia.** Convertir un bolsillo genérico en meta es llenar un campo.

## D-09. Valor del bolsillo: historial; el último registro es el valor actual
**Decisión.** `bolsillo_valor` guarda cada valor que el usuario escribe. No hay columna de valor actual en `bolsillo`.
**Por qué.** Lo fija el enunciado. Guardar además el valor actual en `bolsillo` sería duplicarlo.
**Descartado.** Aportes y retiros (diseño anterior); columna `valor_actual` + historial.
**Consecuencia.** Leer el valor actual requiere buscar el último registro; el índice `(id_bolsillo, registrado_en DESC, id_bolsillo_valor DESC)` lo hace inmediato. El historial es de solo inserción.

## D-10. Bolsillos sin relación con cuentas ni movimientos
**Decisión.** Ninguna FK une `bolsillo` con `cuenta` o `movimiento`.
**Por qué.** Lo fija el enunciado: la reserva es independiente de dónde esté el dinero; gastar lo reservado son dos acciones separadas.
**Descartado.** El modelo anterior (bolsillo dentro de una cuenta, con movimientos APARTADO y RETIRO).
**Consecuencia.** El disponible se calcula a nivel de usuario, no por cuenta. El total reservado puede superar el saldo total; se avisa y no se bloquea.

## D-11. Saldos y demás datos derivados se calculan
**Decisión.** No se guarda saldo de cuenta, valor actual de bolsillo, total reservado, disponible ni progreso.
**Por qué.** Un dato calculado no puede desincronizarse de sus registros fuente. El volumen de un usuario es pequeño.
**Descartado.** Columna `saldo_actual` actualizada en cada movimiento (exige triggers o disciplina perfecta del backend, y se corrompe con anulaciones y correcciones).
**Consecuencia.** Si algún día el cálculo fuera lento, la solución documentada es un índice o una vista materializada, no un saldo guardado a mano.

## D-12. Ajuste de saldo como movimiento propio, calculado por el sistema *(Confirmada)*
**Decisión.** El usuario indica el saldo real; el sistema registra la diferencia como AJUSTE_AUMENTO o AJUSTE_DISMINUCION, con motivo obligatorio y sin categoría. Los ajustes no cuentan como ingreso ni gasto en los resúmenes.
**Por qué.** El usuario no escribe sobre el saldo (no puede, porque no se guarda): solo puede agregar un registro visible, fechado, explicado y anulable. La historia queda intacta.
**Descartado.**
- Editar el saldo inicial: reescribe el pasado y cambia saldos históricos.
- Registrar el ajuste como INGRESO o EGRESO en una categoría "Ajustes": infla los ingresos o gastos del resumen con dinero que no se ganó ni se gastó en esa fecha.
- Un tipo AJUSTE con monto con signo: rompe la regla "monto siempre mayor que cero".
**Consecuencia.** Dos valores más en el CHECK de `tipo`. Los resúmenes deben mostrar los ajustes aparte.

## D-13. Categorías de dos niveles y padre inmutable *(Confirmada)*
**Decisión.** Categoría y subcategoría, nada más. El padre no cambia después de crear la categoría.
**Por qué.** El enunciado habla de "categorías y subcategorías". Con el padre inmutable no pueden formarse ciclos, así que desaparece el trigger con consulta recursiva del diseño anterior. Con dos niveles, la consolidación es un JOIN sencillo.
**Descartado.** Árbol de profundidad libre con posibilidad de mover ramas (diseño anterior): necesita trigger anticiclos y candados.
**Consecuencia.** El límite de dos niveles lo valida el servicio, no la base. Si más adelante se quieren más niveles, la tabla ya lo soporta (`id_padre` es recursivo): basta quitar la validación y usar una consulta recursiva.

## D-14. Cero triggers
**Decisión.** La versión 1 no tiene triggers ni funciones almacenadas.
**Por qué.** Con el modelo simplificado, todo lo que antes pedía trigger se resolvió de otra forma: restricciones (D-02, D-04, D-07), diseño (D-10, D-11, D-13) o una transacción explícita en el servicio. Para un principiante, la lógica visible en Python se entiende y se depura mejor que la lógica oculta en la base.
**Descartado.** Los 77 triggers del diseño anterior.
**Consecuencia.** Ocho reglas dependen de que el servicio haga bien su trabajo (`MODELO_DATOS.md`, sección 6). Deben tener pruebas. Si alguna resultara frágil, ese es el momento de agregar un trigger, justificado.

## D-15. Borrado lógico reforzado con permisos del rol *(Confirmada)*
**Decisión.** Nada se borra. La aplicación se conecta con un rol sin permiso `DELETE` y sin `UPDATE` sobre `bolsillo_valor`.
**Por qué.** Es una garantía declarativa (un `GRANT`) en lugar de un trigger que rechace el borrado.
**Descartado.** Trigger `prohibir_delete` (diseño anterior); confiar solo en que el backend no borre.
**Consecuencia.** Se necesitan dos roles: uno dueño de las tablas (migraciones) y uno de la aplicación.

## D-16. Tipo de cuenta como CHECK *(Confirmada)*
**Decisión.** `cuenta.tipo` con `CHECK (tipo IN ('EFECTIVO','AHORROS','CORRIENTE','BILLETERA_DIGITAL','OTRA'))`.
**Por qué.** Es una lista corta, fija y sin atributos propios. En el diseño anterior era tabla porque guardaba "es electrónico" para el módulo de renta, que está aplazado.
**Descartado.** Tabla `tipo_cuenta`.
**Consecuencia.** Agregar un tipo es una migración que cambia el CHECK.

## D-17. Correcciones en sitio, sin historial de versiones *(Confirmada)*
**Decisión.** Un movimiento vigente se corrige con UPDATE; solo se registra `actualizado_en`.
**Por qué.** La auditoría avanzada está aplazada. Anular sí deja rastro (la fila se conserva).
**Descartado.** Bitácora de cambios por trigger (diseño anterior).
**Consecuencia.** No se puede saber qué valor tenía un movimiento antes de corregirlo. Aceptado para la versión 1.

## D-18. Flask como API JSON + psycopg + SQL a mano *(Confirmada; cambiada el 21/11/2026)*
**Decisión.** Ver `ARQUITECTURA.md`, sección 2. Flask expone una API JSON bajo `/api/`; ya no renderiza plantillas.
**Por qué.** El curso pide SQL explícito. La interfaz pasó a ser una aplicación React aparte (D-21), así que el servidor responde datos y no HTML.
**Descartado.** ORM (oculta el SQL); plantillas Jinja2 en el servidor (era la propuesta inicial, reemplazada por D-21).
**Consecuencia.** El SQL se escribe y se mantiene a mano en `app/repositorios/`.

## D-19. Migraciones: archivos SQL numerados y un script propio *(Confirmada)*
**Decisión.** `db/migraciones/0001_nombre.sql`, `0002_...`. Un script aplica en orden los que falten y anota cada uno en una tabla de control. Una migración aplicada no se edita: los cambios van en una nueva.
**Por qué.** SQL legible, versionado y explicable. El script cabe en una página.
**Descartado.** Alembic (pensado para SQLAlchemy); ejecutar archivos a mano sin registro.
**Consecuencia.** La tabla de control (`migracion_aplicada`) es infraestructura, no parte del modelo de negocio; por eso no se cuenta entre las seis tablas.

## D-20. Una cuenta solo se archiva con saldo 0
**Decisión.** El servicio rechaza archivar una cuenta cuyo saldo calculado no sea 0. Una cuenta archivada no recibe movimientos, y sus movimientos no se corrigen, anulan ni reactivan mientras siga archivada. Los bolsillos, en cambio, se archivan con cualquier valor y dejan de sumar en el total reservado.
**Por qué.** Decisión del estudiante. Evita que desaparezca dinero del saldo total al archivar: si la cuenta tenía saldo, primero se transfiere o se ajusta, y eso queda en el historial. Un bolsillo es solo una reserva virtual; archivarlo no hace desaparecer dinero, lo libera.
**Descartado.** Archivar con saldo y excluirlo del total (la propuesta inicial): el saldo total bajaría sin ningún movimiento que lo explique.
**Consecuencia.** La regla la valida el servicio dentro de una transacción que bloquea la fila de la cuenta (igual que el ajuste de saldo), para que no entre un movimiento entre el cálculo y el archivado. La base no la garantiza: el saldo es un dato calculado y no puede ir en un CHECK.

## D-21. POO por capas e interfaz React separada *(Confirmada el 21/11/2026)*
**Decisión.** El servidor se programa con orientación a objetos: entidades (`dataclasses`), repositorios y servicios como clases; las rutas siguen siendo funciones de Flask. La interfaz es una aplicación React + Vite + TypeScript en `frontend/` que consume la API JSON.
**Por qué.** La parte de POO se evalúa en otra asignatura y la interfaz en otra. Con capas, la base, los repositorios y los servicios no dependen de la interfaz.
**Descartado.** Funciones sueltas por módulo (propuesta inicial); herencia para los tipos de movimiento (la tabla es una sola, con `tipo`); plantillas Jinja2.
**Consecuencia.** Sesión por cookie con interfaz y API en el mismo origen (proxy de Vite en desarrollo); protección CSRF por JSON obligatorio y encabezado propio (`ARQUITECTURA.md`, sección 6). Requiere Python 3.11 o superior (`enum.StrEnum`).
