# Requisitos — FINANCIA+ versión 1

FINANCIA+ es un administrador de finanzas personales **con registro manual**. El usuario crea
sus cuentas, registra a mano sus ingresos, gastos y transferencias, y organiza reservas de
dinero en bolsillos. No hay conexión con bancos ni billeteras. Moneda: pesos colombianos (COP).

## 1. Requisitos funcionales

| Código | Requisito | Reglas relacionadas |
| --- | --- | --- |
| RF-01 | Registrar usuario con nombre, correo y contraseña; iniciar y cerrar sesión. | RN-01, RN-02 |
| RF-02 | Crear, editar y archivar cuentas manuales (nombre, tipo, saldo inicial). | RN-10 a RN-14 |
| RF-03 | Crear, editar y desactivar categorías y subcategorías de ingreso y de egreso. Recibir categorías por defecto al registrarse. | RN-20 a RN-27 |
| RF-04 | Registrar ingresos: cuenta, monto, categoría de ingreso, fecha y descripción opcional. | RN-30 a RN-32 |
| RF-05 | Registrar egresos: cuenta, monto, categoría de egreso, fecha y descripción opcional. | RN-30 a RN-32 |
| RF-06 | Registrar transferencias entre dos cuentas propias como una sola operación. | RN-33, RN-39 |
| RF-07 | Registrar, en el mismo formulario de la transferencia, cargos opcionales (4×1.000, comisión) con su valor real y su categoría. Guardar todo de forma atómica. | RN-34 a RN-38 |
| RF-08 | Crear, editar y archivar bolsillos genéricos (nombre, descripción). | RN-40, RN-49 |
| RF-09 | Crear bolsillos con meta (monto objetivo obligatorio, fecha objetivo opcional) y ver su progreso. | RN-41, RN-48 |
| RF-10 | Editar directamente el valor de un bolsillo; cada cambio queda en un historial. | RN-42 a RN-47 |
| RF-11 | Ver el saldo calculado de cada cuenta. | RN-11, RN-14 |
| RF-12 | Ver el valor actual de cada bolsillo, su historial y el progreso de las metas. | RN-44, RN-48 |
| RF-13 | Ver saldo total de cuentas, total reservado y disponible no reservado, con aviso si es negativo. | RN-60 a RN-63 |
| RF-14 | Ver el historial de movimientos con filtros por fecha, cuenta, tipo y categoría. | RN-64 |
| RF-15 | Ver un resumen financiero del periodo: ingresos, egresos, balance y totales por categoría (con subcategorías consolidadas). | RN-27, RN-53, RN-64 |
| RF-16 | Anular, reactivar y corregir movimientos sin borrarlos. | RN-70 a RN-73 |
| RF-17 | Ajustar el saldo de una cuenta indicando su saldo real; el sistema registra la diferencia como ajuste. | RN-50 a RN-55 |

Los puntos 1 a 15 del alcance pedido quedan cubiertos por RF-01 a RF-15. RF-16 y RF-17 se
agregan porque el enunciado pide definir anulaciones, correcciones y ajustes de saldo.

## 2. Requisitos no funcionales

| Código | Requisito |
| --- | --- |
| RNF-01 | **Aislamiento entre usuarios.** Ningún usuario lee ni modifica datos de otro. La base lo refuerza con claves foráneas compuestas; el servidor filtra siempre por el usuario de la sesión. |
| RNF-02 | **Seguridad básica.** Contraseñas con hash; consultas parametrizadas (nunca texto concatenado); secretos en variables de entorno, fuera del repositorio; cookies de sesión firmadas. |
| RNF-03 | **Integridad.** Las reglas de datos se declaran en la base (PK, FK, UNIQUE, CHECK). Las operaciones de varios pasos usan transacciones. |
| RNF-04 | **Datos derivados calculados.** Saldos, disponible y progreso se calculan desde los registros fuente. |
| RNF-05 | **Sin pérdida de historia.** Nada se borra físicamente: se archiva, desactiva o anula. |
| RNF-06 | **Esquema explícito y versionado.** La base se define con archivos SQL legibles, numerados, aplicados en orden. Sin ORM que genere el esquema. |
| RNF-07 | **Simplicidad.** El código debe poder explicarlo un estudiante en una sustentación: capas claras, funciones cortas, sin dependencias innecesarias. |
| RNF-08 | **Exactitud monetaria.** Dinero en `numeric(14,2)` en la base y `Decimal` en Python. Nunca `float`. |
| RNF-09 | **Extensibilidad.** Las funcionalidades aplazadas se agregan con migraciones y módulos nuevos, sin rehacer las tablas actuales. |
| RNF-10 | **Mensajes claros.** Los errores de validación se muestran en español y sin detalles técnicos ni datos de otros usuarios. |

## 3. Fuera del alcance de la versión 1

No se implementa y **no se crean tablas** para:

- Integraciones bancarias o con Nequi, Nubank u otras entidades.
- Facturas electrónicas, lectura de PDF/XML.
- Integración con Gmail.
- Tarjetas de crédito y deudas.
- Presupuestos.
- Movimientos recurrentes.
- Informes tributarios.
- Notificaciones avanzadas.
- Auditoría avanzada.
- Clasificación automática con inteligencia artificial.
- División de un movimiento entre varias categorías.
- Varias monedas.
- Recuperar la contraseña por correo ("Olvidé mi contraseña"). Ver 3.1.

### 3.1 Previsto para la versión 2: "Olvidé mi contraseña"

Hoy, si alguien olvida su contraseña, quien administra la base le pone una nueva con
`scripts/cambiar_clave.py`. No se puede "recuperar": solo se guarda el hash (RN-02).
Se dejó para la versión 2 (decisión del estudiante, 27/11/2026) porque necesita una tabla nueva,
enviar correos (un servicio externo que cada instalación tendría que configurar) y cuidar
varios detalles de seguridad. Diseño previsto:

| Pieza | Qué haría |
| --- | --- |
| Migración `0003` | Tabla `restablecimiento_clave`: a qué usuario pertenece, el **hash** de un código aleatorio, cuándo vence y cuándo se usó. Sigue las convenciones del modelo (clave compuesta con `id_usuario`, sin borrado). |
| Envío de correo | Una cuenta de correo para la aplicación (SMTP), con sus datos en el `.env`. En desarrollo puede escribir el enlace en la consola en vez de enviarlo. |
| `POST /api/clave/olvido` | Recibe un correo. Si existe, crea un código aleatorio largo (`secrets`), guarda solo su hash y envía un enlace. **Siempre responde lo mismo**, exista o no el correo, para no revelar quién está registrado. Con límite de solicitudes. |
| `POST /api/clave/restablecer` | Recibe el código y la contraseña nueva (mínimo 8 caracteres). Solo si el código existe, no venció (30 a 60 minutos) y no se usó. Lo marca como usado: sirve **una sola vez**. |
| Interfaz | Enlace "¿Olvidó su contraseña?" en Iniciar sesión y dos pantallas: pedir el enlace y escribir la contraseña nueva. |
| Pruebas | Código vencido, ya usado o inventado; correo inexistente (misma respuesta); la contraseña vieja deja de servir. |

## 4. Criterios de aceptación mínimos

Sirven como base de las pruebas. Los valores son ejemplos.

| Código | Escenario | Resultado esperado |
| --- | --- | --- |
| CA-01 | Cuenta con saldo inicial 100.000; ingreso de 50.000; egreso de 20.000. | Saldo 130.000. |
| CA-02 | Transferir 200.000 de Nequi a Nubank con cargo de 800. | Nequi −200.800; Nubank +200.000; egresos del periodo +800; ingresos sin cambio. |
| CA-03 | La transferencia de CA-02 falla al guardar el cargo (categoría inválida). | No queda ni la transferencia ni el cargo. |
| CA-04 | Anular la transferencia de CA-02. | Saldos como antes; el cargo queda anulado. |
| CA-05 | Egreso con una categoría de tipo INGRESO. | Rechazado. |
| CA-06 | Movimiento de U1 con una cuenta o categoría de U2. | Rechazado; no revela datos de U2. |
| CA-07 | Bolsillo con meta de 1.000.000; el usuario escribe 350.000. | Valor 350.000; progreso 35 %; un registro más en el historial; ningún saldo de cuenta cambia. |
| CA-08 | Escribir −1 como valor de un bolsillo. | Rechazado. |
| CA-09 | 200.000 reservados; transferencia de 100.000 entre cuentas. | El bolsillo sigue en 200.000. |
| CA-10 | Saldo total 300.000 y reservado 350.000. | Disponible −50.000, con aviso; nada se bloquea. |
| CA-11 | Saldo calculado 480.000; el usuario indica saldo real 473.500. | Se crea AJUSTE_DISMINUCION de 6.500; saldo 473.500; los egresos del resumen no cambian. |
| CA-12 | 20.000 en "Alimentación" y 30.000 en su subcategoría "Mercado". | Total de Alimentación 50.000; total de Mercado 30.000. |
| CA-13 | Anular un egreso. | Deja de contar; sigue visible en el historial como anulado. |
| CA-14 | Desactivar una categoría con movimientos. | Sus movimientos se conservan; no se puede usar en uno nuevo. |
| CA-15 | Archivar una cuenta con saldo calculado distinto de 0. | Rechazado con mensaje claro. Con saldo 0 sí se archiva. |
