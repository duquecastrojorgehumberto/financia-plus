# Estado del proyecto — FINANCIA+

Última actualización: 17 de noviembre de 2026. **Actualiza este archivo cada vez que termines una tarea.**

## 1. Resumen en una frase

La base de datos está creada, migrada y **probada (132 pruebas pasan)** en el computador del
estudiante; todavía no hay código de aplicación (clases, servicios, rutas) ni interfaz.

## 2. Estado por categoría

| Categoría | Qué hay |
| --- | --- |
| **Creado** | Estructura de carpetas; `README.md`; 8 documentos en `docs/`; un `LEEME.md` por carpeta; `.env.example`; `.gitignore`; `requirements.txt`. |
| **Configurado** | Nada ejecutable. `.env.example` lista las variables necesarias. `requirements.txt` lista dependencias **sin instalar y sin versiones fijadas**. |
| **Documentado** | Requisitos (17 RF, 10 RNF, 15 criterios), arquitectura, modelo de datos (6 tablas), 54 reglas de negocio, 20 decisiones (todas confirmadas), auditoría del diseño anterior, categorías por defecto, guía de continuidad. |
| **Escrito y revisado, SIN EJECUTAR** | `db/migraciones/0001_esquema_inicial.sql`; `tests/conftest.py`; `tests/test_restricciones_bd.py` (81 pruebas). Ver sección 3. |
| **Implementado y verificado** | **Nada.** Ningún archivo se ha ejecutado contra PostgreSQL. |
| **Pendiente** | Todo lo de la sección 5. |

## 3. Detalle de lo escrito en esta etapa

### 3.1 `db/migraciones/0001_esquema_inicial.sql` (Tarea 3)

| Aspecto | Estado |
| --- | --- |
| Escrito | Sí: 6 tablas, 9 índices, 6 comentarios de tabla y 46 de columna, dentro de `BEGIN ... COMMIT`. |
| Revisado a mano | Sí, línea por línea (lista abajo). |
| Ejecutado en PostgreSQL | **No.** Puede contener errores que solo aparecen al ejecutarlo. |

Qué se revisó:

- **Orden y correspondencia de columnas en las 5 FK compuestas.** Cada una está documentada en el archivo columna por columna y coincide en cantidad, orden y tipo con la restricción UNIQUE a la que apunta.
- **NULL en las FK (MATCH SIMPLE).** En cada FK, la única columna que puede ser NULL es la opcional (`id_padre`, `id_cuenta_destino`, `id_categoria`, `id_transferencia`); `id_usuario`, `tipo` e `id_cuenta` son NOT NULL. Ninguna FK puede "apagarse" por accidente.
- **NULL en `ck_movimiento_forma`.** `tipo` es NOT NULL; toda comparación de valores va acompañada de su `IS NOT NULL` en la misma rama. El CHECK nunca da NULL.
- **Índices únicos parciales.** Vigilan solo filas activas; el de categorías usa `COALESCE(id_padre, 0)` para que dos raíces no puedan llamarse igual, e incluye `tipo` para permitir el mismo nombre en raíces de ingreso y de egreso.
- **Lista de control de la guía:** 4 FK compuestas en `movimiento`; `UNIQUE (id_usuario, id_movimiento, id_cuenta)`; `UNIQUE (id_usuario, id_categoria, tipo)`; CHECK de forma con los cinco tipos; tres índices únicos parciales de nombres; sin `ON DELETE CASCADE`; sin triggers.
- **Comprobaciones de texto** (sin ejecutar SQL): paréntesis y comillas balanceados; 49 nombres de restricción e índice, todos distintos; todos los nombres que usan las pruebas existen en la migración.

Dos precisiones que la revisión agregó al modelo (ya reflejadas en `MODELO_DATOS.md`):

| Precisión | Por qué |
| --- | --- |
| Los nombres (usuario, cuenta, categoría, bolsillo) no admiten espacios al inicio ni al final. | Sin esto, "Nequi" y "Nequi " pasarían como nombres distintos y la regla de unicidad no haría lo que dice. |
| `CHECK (id_transferencia <> id_movimiento)`. | La FK del cargo aceptaría que un egreso se apuntara a sí mismo (mismo usuario, misma cuenta). |

Límites conocidos de la base (los debe cubrir el servicio; hay una prueba que documenta cada uno):

- No comprueba que el movimiento al que apunta un cargo sea de tipo TRANSFERENCIA (RN-34).
- No limita las categorías a dos niveles (RN-21).

Requisito al crear la base: codificación UTF8 y una configuración regional distinta de "C",
para que `lower()` trate bien las letras con tilde en la unicidad de nombres.

### 3.2 `tests/test_restricciones_bd.py` y `tests/conftest.py` (Tarea 5)

| Aspecto | Estado |
| --- | --- |
| Escrito | Sí: 81 funciones de prueba (más casos con los parámetros). |
| Revisado a mano | Sí. Además, comprobación estática de sintaxis de Python (sin ejecutar las pruebas). |
| Ejecutado | **No.** `psycopg` y `pytest` no están instalados; no hay base de pruebas. |

Cada rechazo verifica el tipo de error y el nombre de la restricción. Cubren: estructura
(6 tablas, 0 triggers, 0 cascadas, bolsillos sin relación con cuentas, comentarios completos),
propiedad entre usuarios, tipo de categoría, forma de cada tipo de movimiento con sus casos
NULL, montos y redondeo, cargos de transferencias, nombres únicos entre activos, bolsillos e
historial (incluido el desempate cuando dos registros tienen la misma hora).

**Al ejecutarlas por primera vez es normal que haya que ajustar algo**: no se pudieron probar.
Si una prueba falla, revisar primero si el error está en la prueba y no en el esquema.

## 4. Lo que NO existe todavía

- No existe ninguna base de datos creada. La migración no se ha aplicado.
- No existe la migración `0002` (roles y permisos).
- No existe script de migraciones (`scripts/migrar.py`).
- No existe código Python de aplicación: las carpetas de `app/` solo contienen un `LEEME.md`.
- No existe repositorio Git inicializado.
- No se ha instalado ninguna dependencia ni verificado ninguna versión.
- Los scripts SQL de la "Fase 1" anterior (26 tablas) **no forman parte de este proyecto**.

## 5. Pendiente, en orden sugerido

| # | Tarea | Estado | Requisitos |
| --- | --- | --- | --- |
| 1 | Entorno: Git, entorno virtual, instalar dependencias y fijar versiones | **Hecho** (falta inicializar el repositorio Git) | — |
| 2 | Script de migraciones y su tabla de control | **Hecho y ejecutado** | RNF-06 |
| 3 | Migración `0001`: las 6 tablas | **Hecho: aplicada en `financia` y `financia_pruebas`** | `MODELO_DATOS.md` |
| 4 | Migración `0002`: roles y permisos | Pendiente | D-15 |
| 5 | Pruebas de las restricciones | **Hecho: 132 casos pasan** | CA-05, CA-06, CA-08 |
| 6 | Esqueleto de Flask | Pendiente | `ARQUITECTURA.md` |
| 7 | Autenticación y registro | Pendiente | RF-01, RN-26 |
| 8 | Cuentas (archivar solo con saldo 0) | Pendiente | RF-02, RF-11, RN-12, CA-15 |
| 9 | Categorías | Pendiente | RF-03 |
| 10 | Ingresos, egresos, historial, anular y corregir | Pendiente | RF-04, RF-05, RF-14, RF-16 |
| 11 | Transferencias con cargos | Pendiente | RF-06, RF-07 |
| 12 | Ajustes de saldo | Pendiente | RF-17 |
| 13 | Bolsillos, metas e historial | Pendiente | RF-08 a RF-10, RF-12 |
| 14 | Resumen financiero e indicadores | Pendiente | RF-13, RF-15 |
| 15 | Datos de prueba y pruebas de CA-01 a CA-15 | Pendiente | `REQUISITOS.md`, sección 4 |

**Siguiente paso recomendado:** Tareas 1 y 2, y luego ejecutar la migración `0001` y las
pruebas en una base de pruebas. Corregir lo que aparezca antes de escribir código de aplicación.

## 6. Decisiones confirmadas por el estudiante (17 de noviembre de 2026)

Ya no hay decisiones abiertas.

| # | Pregunta | Respuesta | Dónde quedó |
| --- | --- | --- | --- |
| P-1 | ¿Niveles de categorías? | Dos, con padre inmutable. | D-13, RN-21, RN-22 |
| P-2 | ¿Ajustes aparte, sin contar como ingreso ni gasto? | Sí. | D-12, RN-53 |
| P-3 | ¿Varios cargos por transferencia, desde la cuenta de origen? | Sí. | D-05, RN-34, RN-35 |
| P-4 | ¿Corregir sin guardar la versión anterior? | Sí. | D-17, RN-73 |
| P-5 | ¿Qué pasa al archivar? | **Cambiada:** una cuenta solo se archiva si su saldo calculado es 0 (lo valida el servicio). Los bolsillos archivados dejan de sumar en el total reservado. | D-20, RN-12, RN-49, RN-60, CA-15 |
| P-6 | ¿Flask, psycopg 3, Jinja2 y script propio de migraciones? | Sí; el 21/11 Jinja2 se reemplazó por una API JSON con interfaz React (D-21). | D-18, D-19, D-21 |
| P-7 | ¿Tipos de cuenta? | EFECTIVO, AHORROS, CORRIENTE, BILLETERA_DIGITAL, OTRA. | D-16 |

D-15 (rol de la aplicación sin permiso DELETE) se da por aprobada con el diseño general; no
estaba en la lista de preguntas. Si no se quiere manejar dos roles, hay que decirlo antes de la Tarea 4.

## 7. Riesgos conocidos y aceptados en la versión 1

- **Doble envío de formularios** puede duplicar un movimiento. Mitigación en interfaz; sin control en la base.
- **Ocho reglas dependen de la capa de servicios** y no de la base (`MODELO_DATOS.md`, sección 6). Necesitan pruebas.
- **Sin historial de correcciones** de movimientos.
- **La lectura entre usuarios** depende de que todo repositorio filtre por `id_usuario`; las FK solo protegen la escritura.

## 8. Registro de cambios

| Fecha | Cambio |
| --- | --- |
| 2026-11-17 | Auditoría del diseño anterior, modelo de 6 tablas, estructura de carpetas y documentación inicial. Sin implementación. |
| 2026-11-17 | Confirmadas P-1 a P-7 (P-5 cambiada: archivar cuenta exige saldo 0). Actualizados `REGLAS_NEGOCIO.md`, `DECISIONES_ARQUITECTURA.md` (D-20), `MODELO_DATOS.md`, `REQUISITOS.md` (CA-15) y la guía. |
| 2026-11-17 | Escritos y revisados a mano, **sin ejecutar**: migración `0001_esquema_inicial.sql`, `tests/conftest.py` y `tests/test_restricciones_bd.py`. |
| 2026-11-21 | D-18 cambiada y D-21 nueva: POO por capas, Flask como API JSON e interfaz React + Vite + TypeScript. Actualizados `ARQUITECTURA.md`, `DECISIONES_ARQUITECTURA.md`, `GUIA_CONTINUIDAD_OPUS.md` y `README.md`. Sin código todavía. |
| 2026-11-21 | Escritos, sin ejecutar: `scripts/migrar.py` (Tarea 2), `scripts/preparar_bd.py` y `scripts/preparar_windows.ps1` (Tarea 1: instala programas, crea `.env`, rol, bases, migra y prueba). `tests/conftest.py` ahora lee `.env`. |
| 2026-11-21 | Ejecutado `preparar_windows.ps1` en Windows: Python 3.13.2, PostgreSQL, `.venv`, `.env`, rol `financia_admin`, bases `financia` y `financia_pruebas`, migración `0001` aplicada en ambas. **132 pruebas de restricciones pasan.** Versiones fijadas en `requirements.txt`. |
