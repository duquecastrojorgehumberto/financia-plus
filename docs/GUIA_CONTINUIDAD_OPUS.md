# Guía de continuidad para el siguiente modelo

Lee este archivo completo antes de escribir cualquier cosa. Está pensado para que continúes
el desarrollo de FINANCIA+ **sin repetir el análisis y sin reinterpretar el diseño**.

## 1. Lo esencial en un minuto

- **Qué es:** administrador de finanzas personales con registro manual. Web, un usuario por
  sesión, pesos colombianos.
- **Para quién trabajas:** un estudiante de Base de Datos 1 que empieza a programar. Debe
  poder entender y sustentar cada archivo. **Simple gana a ingenioso.**
- **Estado:** las 15 tareas están hechas y probadas (522 pruebas). La versión 1 de la API está
  completa; lo siguiente es la interfaz React (otra asignatura). Ver `ESTADO_PROYECTO.md`. El detalle está en `ESTADO_PROYECTO.md`.
- **Modelo:** 6 tablas, 0 triggers. Está en `MODELO_DATOS.md`. No lo rediseñes.
- **Stack:** Python 3.11+ + Flask (API JSON) + psycopg 3 + PostgreSQL. SQL escrito a mano.
  **POO por capas** (entidades, repositorios, servicios). Interfaz aparte: React + Vite + TypeScript en `frontend/` (D-21).

## 2. Orden de lectura

1. `ESTADO_PROYECTO.md` — qué existe y qué falta (5 minutos).
2. `MODELO_DATOS.md` — la especificación de la base. Es tu fuente para la migración.
3. `REGLAS_NEGOCIO.md` — las reglas RN-xx que debe cumplir el código.
4. `ARQUITECTURA.md` — capas, flujos y seguridad.
5. `REQUISITOS.md` — RF-xx y criterios de aceptación CA-xx.
6. `DECISIONES_ARQUITECTURA.md` — consulta cuando dudes del porqué de algo. Todas están confirmadas.
7. `AUDITORIA_DISENO_ANTERIOR.md` — solo si te encuentras con material del diseño viejo.

## 3. Reglas de trabajo (obligatorias)

1. **No cambies el modelo de datos por tu cuenta.** Si crees que algo está mal, detente,
   explícalo y pide confirmación. No agregues tablas, columnas ni triggers "por si acaso".
2. **No implementes nada aplazado** (lista en `REQUISITOS.md`, sección 3): facturas, Gmail,
   presupuestos, recurrentes, tarjetas, renta, notificaciones, auditoría, varias categorías.
3. **Una tarea a la vez**, en el orden de la sección 5. Termina, prueba, actualiza
   `ESTADO_PROYECTO.md` y espera aprobación antes de la siguiente.
4. **Entrega archivos completos**, sin "..." ni partes omitidas, con los comandos exactos
   para ejecutarlos y cómo comprobar que funcionan.
5. **Explica en lenguaje sencillo** qué hace cada archivo y qué debe entender el estudiante
   para la sustentación.
6. **Nombres en español** y en `snake_case`, iguales a los de `MODELO_DATOS.md`.
7. **Nunca** incluyas contraseñas, tokens ni credenciales reales. Nada de `DROP DATABASE` ni
   instrucciones destructivas. No borres archivos existentes sin autorización.
8. **Verifica antes de afirmar.** No digas que algo funciona si no lo ejecutaste. No asumas
   versiones de librerías: instálalas y fija las que realmente quedaron.
9. Todas las decisiones (D-01 a D-20) están confirmadas por el estudiante. No las reabras:
   si crees que una está mal, explícalo y espera respuesta antes de tocar nada.

## 4. Reglas técnicas (obligatorias)

### Base de datos
- Todo el esquema va en archivos `db/migraciones/NNNN_descripcion.sql`. Una migración ya
  aplicada **no se edita**; los cambios van en una nueva.
- Cada migración va dentro de `BEGIN; ... COMMIT;` y con comentarios en español por bloque.
- Dinero: `numeric(14,2)`. Claves: `bigint GENERATED ALWAYS AS IDENTITY`.
- Toda FK hacia datos de usuario es **compuesta** con `id_usuario`. Sin `ON DELETE CASCADE`.
- Nombra las restricciones: `pk_`, `fk_`, `uq_`, `ck_`, `ix_` + tabla + propósito
  (ej. `fk_movimiento_categoria`, `ck_movimiento_forma`).
- En los CHECK, usa `IS NULL` / `IS NOT NULL` explícitos. `x IN (...)` deja pasar NULL.
- Agrega `COMMENT ON TABLE` y `COMMENT ON COLUMN` a todo: sirve como diccionario de datos.
- No crees vistas, funciones ni triggers sin justificarlo y sin aprobación.

### Aplicación
- Tres capas: `rutas` → `servicios` → `repositorios`, más `entidades`. Respeta qué hace cada una
  y la forma orientada a objetos de `ARQUITECTURA.md`, secciones 3 y 3.1.
- **Una acción del usuario = un método de servicio = una transacción.**
- Todo método de repositorio recibe `id_usuario` y lo usa en el `WHERE`.
- Las rutas responden JSON bajo `/api/`; nunca HTML.
- El `id_usuario` sale de la sesión. **Nunca** del cuerpo JSON ni de la URL.
- SQL siempre parametrizado: `cur.execute("... WHERE id_cuenta = %s", (id_cuenta,))`.
  Prohibido armar SQL con f-strings, `format` o concatenación.
- Dinero en Python: `Decimal`. Nunca `float`.
- Recurso de otro usuario o inexistente: misma respuesta, 404.
- Errores de la base por restricciones: captúralos en el servicio y conviértelos en un
  mensaje claro en español. No muestres el error técnico al usuario.

### Pruebas
- `pytest` contra una base PostgreSQL de pruebas (variable `DATABASE_URL_PRUEBAS`).
- Cada prueba deja la base como la encontró (transacción con ROLLBACK).
- Cita en cada prueba el código que verifica (RN-xx o CA-xx).

## 5. Tareas, en orden

Cada tarea indica qué entregar y cómo saber que está terminada.

### Tarea 1 — Entorno
- Inicializar Git. Crear entorno virtual. Instalar lo de `requirements.txt` y **fijar las
  versiones instaladas** en ese archivo.
- Escribir en `README.md` los pasos reales de instalación para Windows (crear base de datos
  y roles con comandos exactos, sin contraseñas reales).
- **Terminado cuando:** `python -c "import flask, psycopg"` funciona en el entorno virtual.

### Tarea 2 — Script de migraciones
- `scripts/migrar.py`: lee `DATABASE_URL_MIGRACIONES`, crea si no existe la tabla de control
  `migracion_aplicada (nombre text PRIMARY KEY, aplicada_en timestamptz)`, aplica en orden
  alfabético los `.sql` de `db/migraciones/` que no estén registrados, cada uno en su
  transacción, y lo registra. Se detiene en el primer error.
- **Terminado cuando:** ejecutarlo dos veces seguidas aplica todo la primera vez y nada la segunda.

### Tarea 3 — Migración 0001: esquema
> **Ya está escrita y revisada** (`db/migraciones/0001_esquema_inicial.sql`). Lo que falta es
> ejecutarla en una base vacía. Como todavía no se ha aplicado en ninguna parte, si aparece un
> error se corrige en el mismo archivo. Después de aplicada, no se edita más.

- `db/migraciones/0001_esquema_inicial.sql` con las 6 tablas **exactamente** como en
  `MODELO_DATOS.md`, sección 4: columnas, tipos, NOT NULL, valores por defecto, PK, UNIQUE,
  FK compuestas, CHECK e índices.
- Orden de creación: `usuario`, `cuenta`, `categoria`, `movimiento`, `bolsillo`, `bolsillo_valor`.
- Lista de control antes de entregar:
  - [ ] `movimiento` tiene las 4 FK compuestas de la sección 4.4.
  - [ ] `movimiento` tiene `UNIQUE (id_usuario, id_movimiento, id_cuenta)` (lo exige la FK del cargo).
  - [ ] `categoria` tiene `UNIQUE (id_usuario, id_categoria, tipo)`.
  - [ ] El CHECK de forma cubre los cinco tipos y usa `IS NULL` / `IS NOT NULL`.
  - [ ] Los tres índices únicos parciales de nombres existen.
  - [ ] Ninguna FK tiene `ON DELETE CASCADE`. No hay triggers.
- **Terminado cuando:** se aplica sin errores en una base vacía.

### Tarea 4 — Migración 0002: roles y permisos
- Dar al rol de la aplicación `SELECT, INSERT, UPDATE` sobre las tablas (sin `DELETE`), y
  solo `SELECT, INSERT` sobre `bolsillo_valor` (D-15). El nombre del rol y su contraseña no
  van en el archivo: documenta cómo crearlo.
- **Terminado cuando:** conectado con el rol de la aplicación, un `DELETE` es rechazado.

### Tarea 5 — Pruebas de las restricciones
> **Ya están escritas y revisadas** (`tests/test_restricciones_bd.py`, `tests/conftest.py`), sin
> ejecutar. Lo que falta es correrlas y ajustar lo que falle. Si una prueba falla, revisa primero
> si el error está en la prueba; no cambies el esquema para que pase sin entender por qué.

- `tests/test_restricciones_bd.py`. Como mínimo, comprobar que la base **rechaza**:
  movimiento con cuenta de otro usuario; egreso con categoría de ingreso; subcategoría con
  padre de otro tipo; monto cero o negativo; transferencia con origen = destino; ingreso sin
  categoría; transferencia con categoría; ajuste sin descripción; valor de bolsillo negativo;
  fecha objetivo sin monto objetivo; cargo con cuenta distinta a la de su transferencia;
  dos cuentas activas con el mismo nombre.
- **Terminado cuando:** todas pasan. Estas pruebas son la red de seguridad del resto.

### Tarea 6 — Esqueleto de Flask
- `app/__init__.py` (fábrica de la aplicación), `app/config.py` (lee el entorno),
  `app/bd.py` (conexión y un manejador de transacciones), `app/errores.py` (`ErrorNegocio`,
  `NoEncontrado` y su conversión a JSON), la protección CSRF de `ARQUITECTURA.md` sección 6,
  y `GET /api/salud` que diga si hay conexión con la base.
- **Terminado cuando:** `flask run` responde `GET /api/salud` con `{"bd": "ok"}`.

### Tarea 7 — Autenticación
- Registro, inicio y cierre de sesión (RF-01). Hash de contraseña. Decorador "requiere sesión".
- Al registrar: en la misma transacción, copiar las categorías de
  `db/semillas/LEEME.md` al usuario nuevo (RN-26).
- **Terminado cuando:** un usuario nuevo inicia sesión y ya tiene sus categorías.

### Tarea 8 — Cuentas
- Crear, editar, archivar (solo con saldo 0, RN-12 y CA-15), listar con saldo calculado (RF-02, RF-11; RN-10 a RN-14).
- La consulta de saldo sigue la fórmula de `REGLAS_NEGOCIO.md`, sección 2.

### Tarea 9 — Categorías
- Crear, renombrar, desactivar; dos niveles; padre y tipo inmutables (RF-03; RN-20 a RN-27).

### Tarea 10 — Ingresos, egresos e historial
- Registrar, listar con filtros, corregir, anular y reactivar (RF-04, RF-05, RF-14, RF-16).

### Tarea 11 — Transferencias con cargos
- Un formulario: origen, destino, monto, fecha y cero o más cargos (monto + categoría).
- Un servicio con una transacción (flujo 5.2 de `ARQUITECTURA.md`). Anular en cascada lógica (RN-38).
- **Terminado cuando:** pasan CA-02, CA-03 y CA-04.

### Tarea 12 — Ajustes de saldo
- Formulario "saldo real" + motivo. Flujo 5.4 de `ARQUITECTURA.md` (RN-50 a RN-55).
- **Terminado cuando:** pasa CA-11.

### Tarea 13 — Bolsillos
- Crear (genérico o con meta), editar datos, cambiar valor, ver historial y progreso, archivar
  (RF-08 a RF-10, RF-12; RN-40 a RN-49).
- Consulta del valor actual: el registro más reciente por bolsillo
  (`DISTINCT ON (id_bolsillo) ... ORDER BY id_bolsillo, registrado_en DESC, id_bolsillo_valor DESC`).
- **Terminado cuando:** pasan CA-07, CA-08 y CA-09.

### Tarea 14 — Resumen
- Saldo total, total reservado, disponible (con aviso si es negativo); ingresos, egresos y
  balance del periodo; totales por categoría con subcategorías consolidadas; ajustes aparte
  (RF-13, RF-15; RN-60 a RN-64, RN-27, RN-53).
- **Terminado cuando:** pasan CA-01, CA-10 y CA-12.

### Tarea 15 — Datos de prueba y cierre
- `db/semillas/datos_prueba.sql` con usuarios ficticios y los escenarios CA-01 a CA-15.
- Completar las pruebas de los criterios de aceptación. Actualizar `README.md` y `ESTADO_PROYECTO.md`.

## 6. Errores que debes evitar

| Error | Por qué es grave |
| --- | --- |
| Guardar un saldo o un "valor actual" en una columna | Se desincroniza. Todo dato derivado se calcula (D-11). |
| Relacionar bolsillos con cuentas o con movimientos | Contradice una decisión explícita del estudiante (D-10). |
| Representar la transferencia con dos filas | Reintroduce el riesgo de operación a medias (D-04). |
| Guardar el cargo como columnas de la transferencia | Los reportes de gastos lo omitirían (D-05). |
| Sumar transferencias o ajustes como ingresos o gastos | Falsea el resumen (RN-53, RN-64). |
| Tomar `id_usuario` de la petición | Permite ver o alterar datos ajenos (RN-05). |
| Usar FK simples "porque el backend ya filtra" | Se pierde la protección declarativa (D-02). |
| Agregar triggers para validar lo que ya hace un servicio | Duplica lógica y contradice D-14. |
| Reutilizar los scripts SQL de la Fase 1 anterior | Son de otro modelo (26 tablas). |
| Usar `float` para dinero | Errores de centavos. |

## 7. Cuándo detenerte y preguntar

- Una regla de dos documentos se contradice.
- Una tarea necesita una tabla, columna o trigger que no está en `MODELO_DATOS.md`.
- El estudiante pide algo de la lista de aplazados.
- No puedes ejecutar o probar lo que escribiste.

## 8. Formato de cada entrega

1. Qué hiciste (2 o 3 líneas).
2. Archivos creados o modificados, completos.
3. Comandos exactos para ejecutar y para probar, y el resultado que obtuviste.
4. Qué debe entender el estudiante para la sustentación (lista corta).
5. `ESTADO_PROYECTO.md` actualizado.
6. Dudas o decisiones que requieren confirmación.
