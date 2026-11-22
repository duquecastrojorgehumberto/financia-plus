# Estado del proyecto — FINANCIA+

Última actualización: 22 de noviembre de 2026 (Tarea 11). **Actualiza este archivo cada vez que termines una tarea.**

## 1. Resumen en una frase

La base de datos está creada, migrada (`0001` y `0002`) y probada; la API Flask funciona con
autenticación, cuentas (saldo calculado; archivar solo con saldo 0), categorías, ingresos, egresos,
historial y transferencias con cargos, y **413 pruebas pasan**. Todavía no hay ajustes, bolsillos,
resumen ni interfaz.

## 2. Estado por categoría

| Categoría | Qué hay |
| --- | --- |
| **Implementado y verificado** | Entorno (`.venv` con Python 3.13.2, versiones fijadas); repositorio Git (rama `main`); bases `financia` y `financia_pruebas` con las migraciones `0001` y `0002`; roles `financia_admin` y `financia_app`; `scripts/migrar.py` y `scripts/preparar_bd.py`; esqueleto de la API (`app/`); autenticación (Tarea 7); cuentas (Tarea 8); categorías (Tarea 9); ingresos, egresos e historial (Tarea 10); transferencias con cargos (Tarea 11); 413 pruebas. |
| **Documentado** | Requisitos (17 RF, 10 RNF, 15 criterios), arquitectura, modelo de datos (6 tablas), reglas de negocio, 21 decisiones (todas confirmadas), auditoría del diseño anterior, categorías por defecto, guía de continuidad, instalación y uso diario en `README.md`. |
| **Pendiente** | Tareas 12 a 15 (sección 5). La interfaz React (`frontend/`) se desarrolla en otra asignatura. |

## 3. Detalle de lo hecho

### 3.1 Entorno y Git (Tarea 1)

- Proyecto movido a `C:\Users\thedr\proyectos\financia-plus`. El `.venv` se volvió a crear
  allí con Python 3.13.2 y `requirements.txt` (versiones fijadas y comprobadas con `pip freeze`).
- Repositorio Git con la rama `main`. `.gitignore` excluye `.env`, `.venv/`, `__pycache__/`,
  `.pytest_cache/` y `tests/ultimo_resultado.txt`; se comprobó con `git status` que `.env`
  nunca entró en un commit.
- Se eliminaron `app/plantillas/` y `app/estaticos/` (obsoletas por D-21; solo tenían un `LEEME.md`).

### 3.2 Migración `0001` y pruebas de restricciones (Tareas 2, 3 y 5)

Aplicada en las dos bases; 132 pruebas de restricciones pasan (`tests/test_restricciones_bd.py`).
Cada rechazo verifica el tipo de error y el nombre de la restricción.

Límites conocidos de la base (los debe cubrir el servicio; hay una prueba que documenta cada uno):

- No comprueba que el movimiento al que apunta un cargo sea de tipo TRANSFERENCIA (RN-34).
- No limita las categorías a dos niveles (RN-21).

Requisito al crear la base: codificación UTF8 y una configuración regional distinta de "C",
para que `lower()` trate bien las letras con tilde en la unicidad de nombres.

### 3.3 Migración `0002`: roles y permisos (Tarea 4, D-15)

| Aspecto | Estado |
| --- | --- |
| `db/migraciones/0002_roles_y_permisos.sql` | Aplicada en `financia` y `financia_pruebas`. |
| Permisos de `financia_app` | `SELECT, INSERT, UPDATE` sobre `usuario`, `cuenta`, `categoria`, `movimiento`, `bolsillo`; solo `SELECT, INSERT` sobre `bolsillo_valor`. Ningún `DELETE` ni `TRUNCATE`. Sin acceso a `migracion_aplicada`. |
| Si el rol no existe | La migración se detiene con un mensaje claro y no aplica nada (comprobado antes de crear el rol). |
| Creación del rol | `scripts/preparar_bd.py` crea o actualiza `financia_app` con LOGIN y la contraseña de `DATABASE_URL`. La migración no tiene contraseñas. |
| Pruebas | `tests/test_permisos_bd.py` (16 casos), conectadas como `financia_app`: `DELETE` y `TRUNCATE` rechazados en las seis tablas, `UPDATE` sobre `bolsillo_valor` rechazado, y una prueba de control que inserta y actualiza. |

Nota: la guía decía que el nombre del rol no fuera en el archivo. Va en el archivo porque la
migración debe fallar si `financia_app` no existe (instrucción del estudiante); la contraseña no.

### 3.4 Esqueleto de Flask (Tarea 6)

| Archivo | Qué hace |
| --- | --- |
| `app/__init__.py` | `create_app(config=None)`: fábrica de la aplicación. Cookie `HttpOnly` y `SameSite=Lax`. |
| `app/config.py` | `Config` (`dataclass` congelada) con `Config.desde_entorno()`; falla con mensaje claro si falta `SECRET_KEY` o `DATABASE_URL`. |
| `app/bd.py` | `BaseDatos`: conexión en autocommit con filas como diccionarios; una conexión por petición (en `flask.g`), cerrada al terminar. Transacciones con `with con.transaction():`. |
| `app/errores.py` | `ErrorNegocio` (400) y `NoEncontrado(ErrorNegocio)` (404) convertidos a `{"error": "..."}`; 404/405 de Flask y errores inesperados (500) también en JSON, sin detalles técnicos. |
| `app/csrf.py` | POST, PUT, PATCH y DELETE exigen `Content-Type: application/json` (si no, 415) y `X-Requested-With: financia` (si no, 403). |
| `app/rutas/salud.py` | `GET /api/salud`: `{"bd": "ok"}` (200) o `{"bd": "error"}` (503). |
| `pytest.ini` | Pone la carpeta del proyecto en la ruta de Python para las pruebas. |

Verificado: `tests/test_api_base.py` (13 casos) y el servidor real (`flask --app app run`)
respondió `200 {"bd":"ok"}` contra la base `financia` con el rol `financia_app`, y `415` a un
POST sin JSON.

### 3.5 Autenticación (Tarea 7, RF-01)

| Archivo | Qué hace |
| --- | --- |
| `app/entidades/usuario.py`, `categoria.py` | `Usuario` (con `datos_publicos()`, sin el hash), `Categoria` y `TipoCategoria` (`StrEnum`). |
| `app/repositorios/usuarios.py`, `categorias.py` | `UsuarioRepositorio` y `CategoriaRepositorio`, SQL parametrizado. |
| `app/servicios/autenticacion.py` | `AutenticacionServicio`: `registrar` (usuario + 34 categorías en **una** transacción, RN-26), `iniciar_sesion`, `obtener_usuario_activo`. Hash con Werkzeug (RN-02); correo normalizado (RN-01). |
| `app/servicios/categorias_por_defecto.py` | La lista de `db/semillas/LEEME.md` (13 categorías y 21 subcategorías). |
| `app/sesion.py` | `iniciar`, `cerrar` y el decorador `@requiere_sesion`, que entrega `id_usuario` a la ruta (RN-05). |
| `app/rutas/autenticacion.py` | `POST /api/registro` (201, deja la sesión iniciada); `POST /api/sesion` (iniciar); `GET /api/sesion` (quién está); `DELETE /api/sesion` (cerrar). |
| `app/errores.py` | Nueva clase `NoAutenticado(ErrorNegocio)`: 401. |
| `app/bd.py` | Nuevo método `BaseDatos.liberar()`; las pruebas lo redefinen para deshacer todo al final. |

Verificado:
- `tests/test_autenticacion.py` (28 casos). Las pruebas no dejan datos: la base de pruebas
  tenía 0 usuarios y 0 categorías antes y después de ejecutarlas.
- Servidor real (contra `financia_pruebas`, rol `financia_app`, cookies reales): registro 201,
  cerrar 200, ver sin sesión 401, clave errada 401, iniciar sesión 200, ver sesión 200, y 34
  categorías en la base. El usuario de esa verificación se eliminó después con `financia_admin`.

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-8 a P-10):
- La contraseña debe tener **al menos 8 caracteres** (los documentos no fijaban un mínimo).
- **El registro deja la sesión iniciada** (no hay que iniciar sesión justo después de registrarse).
- `@requiere_sesion` solo mira la cookie; no consulta en cada petición si el usuario sigue activo.
  `GET /api/sesion` sí lo hace. La versión 1 no tiene forma de desactivar usuarios desde la aplicación.

### 3.6 Cuentas (Tarea 8: RF-02, RF-11)

| Archivo | Qué hace |
| --- | --- |
| `app/entidades/cuenta.py` | `Cuenta` (la fila), `TipoCuenta` y `CuentaConSaldo` (cuenta + saldo calculado, por composición; `saldo_negativo()` para el aviso de RN-14). |
| `app/repositorios/cuentas.py` | Una sola consulta del saldo con `LEFT JOIN` + `SUM(CASE ...)` según la fórmula de `REGLAS_NEGOCIO.md` §2 (solo VIGENTES); `obtener_para_actualizar` con `FOR UPDATE`. |
| `app/servicios/cuentas.py` | `CuentaServicio`: crear, editar, archivar, reactivar, listar y obtener. Traduce el índice `uq_cuenta_nombre_activa` a un mensaje en español. |
| `app/rutas/cuentas.py` | `GET`/`POST /api/cuentas` (`?archivadas=1`), `GET`/`PUT /api/cuentas/<id>`, `POST /api/cuentas/<id>/archivar` y `/reactivar`. |
| `app/rutas/entrada.py` | Nuevo `dinero()`: el dinero llega como texto y se convierte a `Decimal`; un número JSON se rechaza. |
| `tests/conftest.py` | `BaseDatosDePrueba`, `con_tx` y `cliente_api` pasaron aquí desde `test_autenticacion.py` para compartirlos. |

Verificado:
- `tests/test_cuentas.py` (50 casos): fórmula completa del saldo (los cinco tipos, anulados,
  otro usuario), CA-01 (130.000), CA-15 (rechazo con saldo positivo o negativo; con saldo 0 sí),
  RN-13, RN-06 (cuenta ajena = 404 en las cuatro acciones), nombres únicos entre activas, API.
- **Bloqueo de la fila (D-20):** con dos conexiones reales, mientras la transacción de archivar
  no termina, un `INSERT` de movimiento en esa cuenta tiene que esperar (`LockNotAvailable` a
  los 0,5 s); al terminar, entra sin esperar.
- Servidor real (contra `financia_pruebas`): crear 201 con saldo `"100000.00"`; archivar con
  saldo 400 con mensaje claro; editar a saldo 0; archivar 200; listado con y sin archivadas;
  cuenta inexistente 404. Los datos de esa verificación se eliminaron después.
- Las pruebas dejan la base de pruebas vacía (0 usuarios, cuentas, categorías y movimientos).

Incidente durante las pruebas (resuelto): la primera versión de la prueba del bloqueo se quedó
esperando para siempre, porque intentaba borrar sus datos mientras su propia transacción aún
tenía el `FOR UPDATE`. Se cortó la ejecución, se borraron a mano el usuario y la categoría que
había dejado en `financia_pruebas`, y la prueba ahora libera el bloqueo antes de limpiar y pone
un tope de 5 s a la limpieza.

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-11 a P-14):
- **Una cuenta archivada no se edita**: primero se reactiva (como sus movimientos, RN-12).
- **Hay acción "reactivar"** (RN-12 la menciona; RF-02 no la nombra). Si al reactivar ya existe
  otra cuenta activa con el mismo nombre, se rechaza y se pide renombrar esa otra.
- **RN-13 cuenta también los movimientos anulados**: un anulado puede reactivarse (RN-71), así
  que el saldo inicial queda fijo en cuanto la cuenta tiene cualquier movimiento.
- **El saldo inicial es opcional al crear** (vale 0, como el valor por defecto de la tabla).

### 3.7 Categorías (Tarea 9: RF-03)

| Archivo | Qué hace |
| --- | --- |
| `app/entidades/categoria.py` | Nuevos `Categoria.datos_publicos()` y `RamaCategoria` (raíz + subcategorías, por composición). |
| `app/repositorios/categorias.py` | `obtener`, `obtener_para_actualizar` (`FOR UPDATE`), `renombrar`, `cambiar_activa`, `desactivar_subcategorias`. |
| `app/servicios/categorias.py` | `CategoriaServicio`: árbol con filtros por tipo y por activas; crear raíz o subcategoría (la subcategoría toma el tipo del padre); máximo dos niveles (RN-21); solo cambia el nombre (RN-22); desactivar (con sus subcategorías) y reactivar. Traduce `uq_categoria_hermanas_activas`. |
| `app/rutas/categorias.py` | `GET`/`POST /api/categorias`, `GET`/`PUT /api/categorias/<id>`, `POST …/desactivar` y `…/reactivar`. |
| `app/rutas/entrada.py` | Nuevos `entero_opcional` (rechaza `true`, textos y decimales) y `solo_campos` (rechaza campos no permitidos). |

Orden de los bloqueos: `desactivar` y `reactivar` bloquean siempre primero la categoría padre y
después la hija, para que dos peticiones simultáneas no puedan esperarse mutuamente (deadlock).

Verificado:
- `tests/test_categorias.py` (48 casos): RN-20 a RN-25, CA-14 (los movimientos de una categoría
  desactivada se conservan y siguen contando en el saldo), RN-06, árbol de las categorías por
  defecto (13 raíces, 21 subcategorías) y API.
- Servidor real (contra `financia_pruebas`): árbol de egresos (9 raíces, 17 subcategorías);
  crear raíz y subcategoría; tercer nivel rechazado; cambiar el tipo rechazado; renombrar;
  desactivar la raíz desactiva su subcategoría; la hija no se reactiva con el padre desactivado;
  nombre repetido rechazado. Los datos de la verificación se eliminaron después.
- Las pruebas dejan la base de pruebas vacía.

Pendiente para la Tarea 10: CA-14 también exige que una categoría desactivada **no se pueda usar
en un movimiento nuevo**. Eso lo debe validar el servicio de movimientos, leyendo la categoría con
bloqueo (`FOR SHARE` o `FOR UPDATE`) para que no la desactiven entre la revisión y el `INSERT`.

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-15 a P-19):
- **Desactivar una raíz desactiva también sus subcategorías activas**, en la misma transacción.
  Una subcategoría activa bajo un padre desactivado sería confusa en los totales (RN-27).
- **Reactivar una raíz no reactiva sus subcategorías**; cada una se reactiva aparte, y una
  subcategoría solo se reactiva si su padre está activo.
- **Una categoría desactivada no se renombra** (como las cuentas archivadas, P-11).
- **Si el cuerpo de `PUT` trae `tipo` o `id_padre`, se responde 400** en lugar de ignorarlos (RN-22).
- **"Impuestos y comisiones" no tiene protección especial**: se puede renombrar o desactivar como
  cualquier otra. RN-26 solo exige que el usuario la reciba al registrarse. En la Tarea 11, el
  formulario de transferencias la propondría para los cargos si existe activa con ese nombre.
  La alternativa es impedir renombrarla y desactivarla, pero identificarla por el nombre es frágil.

### 3.8 Ingresos, egresos e historial (Tarea 10: RF-04, RF-05, RF-14, RF-16)

| Archivo | Qué hace |
| --- | --- |
| `app/entidades/movimiento.py` | `Movimiento` (una clase para los cinco tipos, sin herencia, D-03), `TipoMovimiento`, `EstadoMovimiento`, `MovimientoDetalle` (movimiento + nombres, por composición). |
| `app/repositorios/movimientos.py` | Historial en **una sola consulta** con filtros opcionales `(%(filtro)s IS NULL OR condición)`; insertar, corregir (marca `actualizado_en`, RN-73) y cambiar estado. |
| `app/repositorios/cuentas.py`, `categorias.py` | Nuevo `obtener_para_usar` con `FOR SHARE`. |
| `app/servicios/movimientos.py` | `MovimientoServicio`: registrar ingreso o egreso; corregir (RN-72); anular (RN-70) y reactivar (RN-71); historial. Valida cuenta activa (RN-12), categoría activa y del mismo tipo (RN-25, RN-31) y propiedad (RN-06). |
| `app/servicios/validaciones.py` | `validar_dinero`, compartida con `CuentaServicio`. |
| `app/rutas/movimientos.py` | `GET`/`POST /api/movimientos`, `GET`/`PUT /api/movimientos/<id>`, `POST …/anular` y `…/reactivar`. |
| `app/rutas/entrada.py` | Nuevos `entero`, `texto_opcional`, `fecha` y los parámetros de URL `parametro_fecha`, `parametro_entero`, `parametro_texto`. |

Verificado:
- `tests/test_movimientos.py` (73 casos): CA-01, CA-05, CA-06, CA-13, **CA-14 completo** (la
  categoría desactivada ya no se puede usar en un movimiento nuevo), RN-12, RN-30, RN-31, RN-70
  a RN-73, cada filtro del historial, RN-06 y API.
- **Carreras reales entre dos conexiones:** si la cuenta se archiva (o la categoría se desactiva)
  mientras se registra un movimiento, el registro espera y lo rechaza. **Prueba de mutación:** al
  quitar el `FOR SHARE`, las dos pruebas fallan (se guardaba un movimiento en una cuenta
  archivada); con él, pasan. La misma comprobación se hizo con la prueba del `FOR UPDATE` de la
  Tarea 8: también falla sin él.
- Una primera versión de esas pruebas pasaba también sin `FOR SHARE` (el `INSERT` ya bloquea la
  cuenta al revisar la FK), así que no demostraba nada; se reescribió para reproducir la carrera
  en el momento que el `FOR SHARE` protege: entre la revisión y el `INSERT`.
- Servidor real (contra `financia_pruebas`): CA-01 (130.000), CA-05, CA-13 (anulado, saldo vuelve),
  CA-14, filtro por categoría con subcategorías y corrección. Datos de la verificación eliminados.
- Las pruebas dejan la base de pruebas vacía.

Qué queda para otras tareas (el servicio lo rechaza con un mensaje claro):
- **Tarea 11:** anular y reactivar una transferencia (debe hacerse en cascada con sus cargos,
  RN-38) y corregir transferencias y cargos. Un cargo ya se puede anular solo, y solo se
  reactiva si su transferencia está vigente.
- **Tarea 12:** registrar y corregir ajustes. Anularlos y reactivarlos ya funciona (RN-54).

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-20 a P-24):
- **Una sola ruta para ingresos y egresos** (`POST /api/movimientos` con `tipo`), en lugar de dos.
- **El filtro por categoría incluye sus subcategorías**, y **el filtro por cuenta incluye las
  transferencias que entran** a ella. El historial muestra los anulados salvo que se filtre por estado.
- **Al corregir, se puede conservar una categoría que se desactivó después**; solo se exige que
  esté activa si se cambia por otra. **Reactivar** un movimiento tampoco exige que su categoría
  siga activa (no es un movimiento nuevo).
- **Se aceptan fechas futuras** (por ejemplo, un pago programado). Los documentos no lo limitan.
- **El historial no tiene paginación**: devuelve todos los movimientos que cumplen los filtros.

### 3.9 Transferencias con cargos (Tarea 11: RF-06, RF-07)

| Archivo | Qué hace |
| --- | --- |
| `app/entidades/movimiento.py` | Nuevo `TransferenciaConCargos` (transferencia + cargos, por composición; `total_cargos_vigentes()`). |
| `app/repositorios/movimientos.py` | Nuevos `insertar_transferencia`, `insertar_cargo`, `listar_cargos`, `bloquear_cargos` (`FOR UPDATE`), `corregir_transferencia`, `cambiar_fecha_cargos`, `corregir_cargo`; filtro `id_transferencia` en `listar`. |
| `app/servicios/transferencias.py` | `TransferenciaServicio`: registrar (flujo 5.2 de `ARQUITECTURA.md`: transferencia + cargos en una transacción), corregir, agregar y corregir cargos, anular en cascada (RN-38) y reactivar. |
| `app/servicios/verificaciones.py` | `VerificadorDeUso`: las comprobaciones de cuenta activa y categoría utilizable salieron de `MovimientoServicio` para compartirlas sin copiar código. |
| `app/rutas/transferencias.py` | `POST /api/transferencias`, `GET`/`PUT /api/transferencias/<id>`, `POST …/anular`, `…/reactivar`, `…/cargos` y `PUT …/cargos/<id_cargo>`. |
| `tests/conftest.py` | `Mundo` pasó aquí desde `test_movimientos.py` para compartirlo. |

Orden de los bloqueos, siempre el mismo: transferencia → cargos → cuentas y categorías.

Verificado:
- `tests/test_transferencias.py` (53 casos): CA-02 (Nequi −200.800, Nubank +200.000, egresos +800,
  ingresos sin cambio), CA-03 (cargo con categoría de ingreso, de otro usuario, y una falla técnica
  simulada en el segundo cargo: en los tres casos no queda nada), CA-04, RN-33 a RN-38, RN-72,
  RN-12, RN-06 y API.
- **Prueba de mutación:** al quitar la transacción de `registrar`, las tres pruebas de CA-03 fallan
  (quedaban la transferencia y el primer cargo); con ella, pasan.
- Servidor real (contra `financia_pruebas`): CA-02, CA-03, CA-04, anular desde `/api/movimientos`
  rechazado y reactivar. Datos de la verificación eliminados.
- Las pruebas dejan la base de pruebas vacía.

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-25 a P-28):
- **Reactivar una transferencia no reactiva sus cargos**: cada uno se reactiva aparte en
  `/api/movimientos/<id>/reactivar`. Al anular no se guarda cuáles cargos ya estaban anulados a
  propósito, y reactivarlos todos podría revivir uno de esos.
- **Corregir la fecha de una transferencia cambia también la fecha de sus cargos** (RN-35 exige que
  sea la misma). Corregir el monto no cambia los cargos.
- **Se puede agregar un cargo a una transferencia ya registrada** (`POST …/cargos`), por si se olvidó
  el 4×1.000. RF-07 solo habla del formulario de registro.
- **La API no propone "Impuestos y comisiones"**: la interfaz la encuentra por nombre en el árbol de
  categorías y la preselecciona (P-19: no tiene protección especial).

## 4. Lo que NO existe todavía

- Módulos de ajustes, bolsillos y resumen: sin repositorios, servicios ni rutas (Tareas 12 a 14).
- No hay datos de prueba (`db/semillas/datos_prueba.sql`).
- No hay interfaz (`frontend/`).
- El repositorio Git no tiene remoto (no se ha subido a GitHub).
- Los scripts SQL de la "Fase 1" anterior (26 tablas) **no forman parte de este proyecto**.

## 5. Pendiente, en orden sugerido

| # | Tarea | Estado | Requisitos |
| --- | --- | --- | --- |
| 1 | Entorno: Git, entorno virtual, instalar dependencias y fijar versiones | **Hecho** | — |
| 2 | Script de migraciones y su tabla de control | **Hecho y ejecutado** | RNF-06 |
| 3 | Migración `0001`: las 6 tablas | **Hecho: aplicada en las dos bases** | `MODELO_DATOS.md` |
| 4 | Migración `0002`: roles y permisos | **Hecho: aplicada en las dos bases; 16 pruebas** | D-15 |
| 5 | Pruebas de las restricciones | **Hecho: 132 casos pasan** | CA-05, CA-06, CA-08 |
| 6 | Esqueleto de Flask | **Hecho: `/api/salud` responde; 13 pruebas** | `ARQUITECTURA.md` |
| 7 | Autenticación y registro | **Hecho: 28 pruebas; servidor probado** | RF-01, RN-26 |
| 8 | Cuentas (archivar solo con saldo 0) | **Hecho: 50 pruebas; servidor probado** | RF-02, RF-11, RN-12, CA-15 |
| 9 | Categorías | **Hecho: 48 pruebas; servidor probado** | RF-03 |
| 10 | Ingresos, egresos, historial, anular y corregir | **Hecho: 73 pruebas; servidor probado** | RF-04, RF-05, RF-14, RF-16 |
| 11 | Transferencias con cargos | **Hecho: 53 pruebas; servidor probado** | RF-06, RF-07 |
| 12 | Ajustes de saldo | Pendiente (**esperando aprobación**) | RF-17 |
| 13 | Bolsillos, metas e historial | Pendiente | RF-08 a RF-10, RF-12 |
| 14 | Resumen financiero e indicadores | Pendiente | RF-13, RF-15 |
| 15 | Datos de prueba y pruebas de CA-01 a CA-15 | Pendiente | `REQUISITOS.md`, sección 4 |

**Siguiente paso recomendado:** Tarea 12 (ajustes de saldo), cuando el estudiante la apruebe.

## 6. Decisiones confirmadas por el estudiante (17 y 22 de noviembre de 2026)

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
| P-8 | ¿Longitud mínima de la contraseña? (22/11) | 8 caracteres. | `LONGITUD_MINIMA_CLAVE` en `app/servicios/autenticacion.py` |
| P-9 | ¿El registro deja la sesión iniciada? (22/11) | Sí. | `POST /api/registro` |
| P-10 | ¿`@requiere_sesion` revisa en cada petición si el usuario sigue activo? (22/11) | No: solo la cookie. `GET /api/sesion` sí lo revisa. | `app/sesion.py` |
| P-11 | ¿Se puede editar una cuenta archivada? (22/11) | No: primero se reactiva. | `CuentaServicio.editar` |
| P-12 | ¿Existe la acción "reactivar cuenta"? (22/11) | Sí. Si otra cuenta activa tiene el mismo nombre, se rechaza y se pide renombrar esa otra. | `CuentaServicio.reactivar` |
| P-13 | ¿Los movimientos anulados fijan el saldo inicial (RN-13)? (22/11) | Sí: cualquier movimiento, vigente o anulado. | `CuentaRepositorio.tiene_movimientos` |
| P-14 | ¿El saldo inicial es obligatorio al crear? (22/11) | No: si no se envía, vale 0. | `POST /api/cuentas` |
| P-15 | ¿Desactivar una raíz desactiva sus subcategorías? (22/11) | Sí, en la misma transacción. | `CategoriaServicio.desactivar` |
| P-16 | ¿Reactivar una raíz reactiva sus subcategorías? (22/11) | No: cada una aparte, y solo con el padre activo. | `CategoriaServicio.reactivar` |
| P-17 | ¿Se renombra una categoría desactivada? (22/11) | No: primero se reactiva. | `CategoriaServicio.renombrar` |
| P-18 | ¿Qué pasa si al renombrar llegan `tipo` o `id_padre`? (22/11) | Se responde 400; no se ignoran. | `PUT /api/categorias/<id>` |
| P-19 | ¿"Impuestos y comisiones" tiene protección especial? (22/11) | No: se renombra o desactiva como cualquier otra. | RN-26 |
| P-20 | ¿Una ruta o dos para ingresos y egresos? (22/11) | Una: `POST /api/movimientos` con `tipo`. | `app/rutas/movimientos.py` |
| P-21 | ¿Qué incluyen los filtros del historial? (22/11) | Categoría: también sus subcategorías. Cuenta: también las transferencias que entran. Los anulados se muestran salvo que se filtre por estado. | `MovimientoRepositorio.listar` |
| P-22 | ¿Corregir o reactivar exige que la categoría siga activa? (22/11) | No, si la categoría no cambia: no es un movimiento nuevo. Una categoría nueva sí debe estar activa. | `MovimientoServicio.corregir` y `reactivar` |
| P-23 | ¿Se aceptan fechas futuras? (22/11) | Sí. | `MovimientoServicio` |
| P-24 | ¿El historial tiene paginación? (22/11) | No: devuelve todos los que cumplen los filtros. | `GET /api/movimientos` |
| P-25 | ¿Reactivar una transferencia reactiva sus cargos? (22/11) | No: cada cargo se reactiva aparte. | `TransferenciaServicio.reactivar` |
| P-26 | ¿Corregir la fecha de una transferencia cambia la de sus cargos? (22/11) | Sí (RN-35). Corregir el monto no toca los cargos. | `TransferenciaServicio.corregir` |
| P-27 | ¿Se puede agregar un cargo a una transferencia ya registrada? (22/11) | Sí. | `POST /api/transferencias/<id>/cargos` |
| P-28 | ¿La API propone "Impuestos y comisiones" para los cargos? (22/11) | No: la interfaz la busca por nombre y la preselecciona. | Interfaz (`frontend/`) |

D-15 (rol de la aplicación sin permiso DELETE) quedó implementada en la Tarea 4 con dos roles:
`financia_admin` (migraciones) y `financia_app` (aplicación).

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
| 2026-11-22 | Proyecto movido a `C:\Users\thedr\proyectos\financia-plus`; `.venv` recreado (132 pruebas pasan). Repositorio Git inicializado (rama `main`); eliminadas `app/plantillas/` y `app/estaticos/`. |
| 2026-11-22 | Tarea 4: migración `0002_roles_y_permisos.sql` aplicada en las dos bases; `preparar_bd.py` crea `financia_app`; `tests/test_permisos_bd.py`. **148 pruebas pasan.** |
| 2026-11-22 | Tarea 6: esqueleto de Flask (`app/__init__.py`, `config.py`, `bd.py`, `errores.py`, `csrf.py`, `rutas/salud.py`), `pytest.ini`, `tests/test_api_base.py`; `README.md` con instalación y uso diario. Servidor probado. **161 pruebas pasan.** |
| 2026-11-22 | Tarea 7: autenticación (entidades, repositorios y servicio de usuario y categoría; sesión y `@requiere_sesion`; rutas `/api/registro` y `/api/sesion`); `tests/test_autenticacion.py`. Servidor probado. **189 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-8 a P-10 (contraseña de 8 caracteres o más, el registro inicia sesión, `@requiere_sesion` solo revisa la cookie). |
| 2026-11-22 | Tarea 8: cuentas (entidad `Cuenta`/`CuentaConSaldo`, `CuentaRepositorio` con el saldo calculado, `CuentaServicio`, rutas `/api/cuentas`); `tests/test_cuentas.py` con prueba real del bloqueo `FOR UPDATE`. Servidor probado. **239 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-11 a P-14 (cuenta archivada no se edita, reactivar, anulados fijan el saldo inicial, saldo inicial opcional). |
| 2026-11-22 | Tarea 9: categorías (`RamaCategoria`, `CategoriaRepositorio` ampliado, `CategoriaServicio`, rutas `/api/categorias`); `tests/test_categorias.py`. Servidor probado. **287 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-15 a P-19 (categorías: desactivar con subcategorías, reactivar una a una, desactivada no se renombra, 400 si llegan tipo o padre, sin protección especial para "Impuestos y comisiones"). |
| 2026-11-22 | Tarea 10: ingresos, egresos e historial (`Movimiento`, `MovimientoRepositorio`, `MovimientoServicio`, rutas `/api/movimientos`, `FOR SHARE` en cuentas y categorías); `tests/test_movimientos.py` con carreras reales y pruebas de mutación. Servidor probado. **360 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-20 a P-24 (una ruta para ingresos y egresos, filtros del historial, categoría desactivada en correcciones y reactivaciones, fechas futuras, sin paginación). |
| 2026-11-22 | Tarea 11: transferencias con cargos (`TransferenciaServicio`, `VerificadorDeUso`, `TransferenciaConCargos`, rutas `/api/transferencias`); `tests/test_transferencias.py` con CA-02, CA-03 y CA-04 y prueba de mutación de la transacción. Servidor probado. **413 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-25 a P-28 (reactivar transferencia sin sus cargos, la fecha de los cargos sigue a la transferencia, agregar cargos después, la interfaz preselecciona "Impuestos y comisiones"). |
