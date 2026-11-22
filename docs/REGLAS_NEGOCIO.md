# Reglas de negocio — FINANCIA+ versión 1

Cada regla tiene un código (RN-xx) para citarla en el código, las pruebas y los commits.
La columna "Dónde" dice quién la hace cumplir: **BD** (restricción de la base) o **Servicio**
(capa de servicios de la aplicación, dentro de una transacción).

## 1. Usuarios y propiedad

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-01 | El correo es único y se guarda en minúsculas. | BD |
| RN-02 | La contraseña se guarda solo como hash. | Servicio |
| RN-03 | Cada cuenta, categoría, movimiento y bolsillo pertenece a un solo usuario. | BD |
| RN-04 | Un registro solo puede relacionarse con registros del mismo usuario. | BD (FK compuestas) |
| RN-05 | El `id_usuario` de toda operación sale de la sesión del servidor, nunca de un dato enviado por el navegador. | Servicio |
| RN-06 | Si un usuario pide un registro ajeno, la respuesta es "no encontrado", igual que si no existiera. | Servicio |

## 2. Cuentas

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-10 | Una cuenta tiene nombre, tipo y saldo inicial (cero o positivo). | BD |
| RN-11 | El saldo actual se calcula; nunca se guarda ni se escribe a mano. | Diseño |
| RN-12 | Una cuenta no se borra: se archiva. **Solo se puede archivar si su saldo calculado es 0**; si tiene saldo, primero hay que transferirlo o ajustarlo. Archivada no admite movimientos nuevos, y sus movimientos no se corrigen, anulan ni reactivan mientras siga archivada (hay que reactivarla primero). Así su saldo permanece en 0. | Servicio |
| RN-13 | El saldo inicial solo se puede editar mientras la cuenta no tenga movimientos. Después, las correcciones se hacen con un ajuste (RN-50). | Servicio |
| RN-14 | El saldo calculado puede ser negativo: no se bloquea, se muestra con un aviso. | Servicio |

Fórmula del saldo (solo movimientos VIGENTES):

```
saldo = saldo_inicial
      + INGRESOS de la cuenta
      - EGRESOS de la cuenta            (incluye los cargos de transferencias)
      - TRANSFERENCIAS donde la cuenta es origen
      + TRANSFERENCIAS donde la cuenta es destino
      + AJUSTES_AUMENTO
      - AJUSTES_DISMINUCION
```

## 3. Categorías

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-20 | Cada categoría es de tipo INGRESO o EGRESO. | BD |
| RN-21 | Hay como máximo dos niveles: categoría y subcategoría. | Servicio |
| RN-22 | El padre y el tipo de una categoría no cambian después de creada. Para reorganizar: crear otra y desactivar la anterior. | Servicio |
| RN-23 | La subcategoría es del mismo usuario y del mismo tipo que su padre. | BD |
| RN-24 | No se repite el nombre entre hermanas activas (ni entre raíces del mismo tipo). | BD |
| RN-25 | Una categoría no se borra: se desactiva. Conserva su historia y no admite movimientos nuevos. | Servicio |
| RN-26 | Al registrarse, el usuario recibe una copia de las categorías por defecto, entre ellas "Impuestos y comisiones" (EGRESO). | Servicio |
| RN-27 | El total de una categoría incluye el de sus subcategorías, contando cada movimiento una sola vez. | Consulta |

## 4. Ingresos y egresos

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-30 | Un ingreso o egreso tiene cuenta, monto mayor que cero, fecha y **una sola** categoría. La descripción es opcional. | BD |
| RN-31 | La categoría de un ingreso es de tipo INGRESO; la de un egreso, de tipo EGRESO. | BD |
| RN-32 | Se puede asignar una categoría raíz o una subcategoría, nunca las dos. | BD (una sola columna) |

## 5. Transferencias y cargos

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-33 | Una transferencia es **un solo registro** con cuenta de origen y cuenta de destino distintas. No es ingreso ni gasto y no tiene categoría. | BD |
| RN-34 | Una transferencia puede tener cero o más cargos (4×1.000, comisión...). Cada cargo es un EGRESO normal, con su categoría, que apunta a la transferencia. | BD + Servicio |
| RN-35 | El cargo sale de la cuenta de origen de la transferencia y lleva su misma fecha. | BD (cuenta) + Servicio (fecha) |
| RN-36 | El usuario escribe el valor real del cargo. El sistema no calcula tarifas ni porcentajes. | Servicio |
| RN-37 | La transferencia y sus cargos se guardan en una sola transacción: todos o ninguno. | Servicio |
| RN-38 | Anular una transferencia anula también sus cargos, en la misma transacción. Un cargo sí puede anularse solo. | Servicio |
| RN-39 | Las transferencias no modifican ningún bolsillo. | Diseño (no hay relación) |

Ejemplo (RN-33 a RN-37). Transferir $200.000 de Nequi a Nubank con un cargo de $800:

| Registro | tipo | id_cuenta | id_cuenta_destino | id_categoria | id_transferencia | monto |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | TRANSFERENCIA | Nequi | Nubank | — | — | 200.000 |
| M2 | EGRESO | Nequi | — | Impuestos y comisiones | M1 | 800 |

Resultado: Nequi baja 200.800; Nubank sube 200.000; los gastos del periodo suben 800.
El cargo aparece solo en cualquier reporte de egresos, sin consultas especiales.

## 6. Bolsillos y metas

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-40 | Un bolsillo es una reserva virtual. No pertenece a ninguna cuenta. | Diseño |
| RN-41 | Es "con meta" si tiene monto objetivo (mayor que cero). La fecha objetivo es opcional y solo existe si hay monto objetivo. | BD |
| RN-42 | El usuario escribe directamente el valor que quiere tener reservado. No hay aportes ni retiros. | Diseño |
| RN-43 | El valor no puede ser negativo; puede ser cero. | BD |
| RN-44 | Cada cambio de valor agrega un registro al historial (fecha y nuevo valor). El valor actual es el del registro más reciente. | Servicio |
| RN-45 | Al crear un bolsillo se crea su primer registro de historial (cero si el usuario no indica otro valor), en la misma transacción. | Servicio |
| RN-46 | Si el valor nuevo es igual al actual, no se agrega registro. | Servicio |
| RN-47 | Cambiar el valor no es ingreso ni gasto y no modifica ninguna cuenta. Gastar dinero reservado son dos acciones independientes: registrar el egreso y, si el usuario quiere, bajar el valor del bolsillo. | Diseño |
| RN-48 | Progreso de la meta = valor actual ÷ monto objetivo. Puede pasar del 100 %. | Consulta |
| RN-49 | Un bolsillo no se borra: se archiva, con cualquier valor. Archivado no suma en el total reservado y conserva su historial. | Servicio |

Ejemplo (RN-39). Hay $200.000 reservados para un computador. Se transfieren $100.000 de Nequi
a Nubank. El bolsillo sigue mostrando $200.000: la reserva no depende de dónde esté el dinero.

## 7. Ajustes de saldo

Problema: el usuario olvida registrar algo y el saldo de FINANCIA+ deja de coincidir con el
del banco. No debe poder "escribir encima" del saldo, porque se perdería la historia.

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-50 | El usuario indica el **saldo real** de la cuenta. El sistema calcula la diferencia con el saldo calculado y registra un movimiento de ajuste por esa diferencia. | Servicio |
| RN-51 | Diferencia positiva → AJUSTE_AUMENTO; negativa → AJUSTE_DISMINUCION; cero → no se registra nada. El monto siempre es positivo. | Servicio + BD |
| RN-52 | El ajuste lleva una descripción obligatoria (motivo) y no tiene categoría. | BD |
| RN-53 | Los ajustes cambian el saldo de la cuenta pero **no** cuentan como ingresos ni gastos en los resúmenes; se muestran aparte. | Consulta |
| RN-54 | El ajuste queda en el historial como cualquier movimiento y se puede anular. | Diseño |
| RN-55 | El cálculo y el registro del ajuste ocurren en una transacción que bloquea la fila de la cuenta, para que nadie registre otro movimiento en medio. | Servicio |

Ejemplo. FINANCIA+ calcula $480.000 en Nequi; la app de Nequi muestra $473.500. El usuario
escribe 473.500 y el motivo "compras no registradas". Se crea un AJUSTE_DISMINUCION de $6.500.
El saldo queda en $473.500 y el historial muestra cuándo y por qué se ajustó.

Si después el usuario recuerda el gasto real, lo correcto es anular el ajuste y registrar el
egreso con su categoría.

## 8. Indicadores

| Código | Regla |
| --- | --- |
| RN-60 | Saldo total de cuentas = suma de los saldos de las cuentas activas. Las archivadas no cambian el resultado porque su saldo es 0 (RN-12). |
| RN-61 | Total reservado = suma de los valores actuales de los bolsillos activos. |
| RN-62 | Disponible no reservado = saldo total − total reservado. |
| RN-63 | Si el disponible es negativo no se bloquea nada: se muestra negativo y con un aviso. |
| RN-64 | Ingresos y egresos de un periodo = movimientos VIGENTES de tipo INGRESO y EGRESO en ese rango de fechas. Transferencias y ajustes no entran. |

## 9. Anulaciones y correcciones

| Código | Regla | Dónde |
| --- | --- | --- |
| RN-70 | Ningún movimiento se borra físicamente. Anular cambia `estado` a ANULADO y deja de contar. | BD (sin permiso DELETE) + Servicio |
| RN-71 | Un movimiento anulado se puede reactivar. | Servicio |
| RN-72 | De un movimiento VIGENTE se pueden corregir monto, fecha, categoría, cuenta y descripción. El tipo no cambia: si el tipo estaba mal, se anula y se crea otro. La cuenta de origen de una transferencia que tiene cargos tampoco se cambia (la FK del cargo lo impediría): se anula y se registra de nuevo. | Servicio |
| RN-73 | Al corregir, se actualiza `actualizado_en`. No se guarda historial de versiones (la auditoría avanzada está aplazada). | Servicio |
