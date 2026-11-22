# Estado del proyecto — FINANCIA+

Última actualización: 22 de noviembre de 2026 (Tarea 15: cierre de la versión 1). **Actualiza este archivo cada vez que termines una tarea.**

## 1. Resumen en una frase

La base de datos está creada, migrada (`0001` y `0002`) y probada; la API Flask funciona con
autenticación, cuentas (saldo calculado; archivar solo con saldo 0), categorías, ingresos, egresos,
historial, transferencias con cargos, ajustes de saldo, bolsillos con metas y resumen financiero.
**Las 15 tareas de la guía están terminadas y 522 pruebas pasan.** Hay datos de demostración
para la sustentación. Lo único que falta es la interfaz React, que se hace en otra asignatura.

## 2. Estado por categoría

| Categoría | Qué hay |
| --- | --- |
| **Implementado y verificado** | Entorno (`.venv` con Python 3.13.2, versiones fijadas); repositorio Git (rama `main`); bases `financia` y `financia_pruebas` con las migraciones `0001` y `0002`; roles `financia_admin` y `financia_app`; `scripts/migrar.py` y `scripts/preparar_bd.py`; esqueleto de la API (`app/`); autenticación (Tarea 7); cuentas (Tarea 8); categorías (Tarea 9); ingresos, egresos e historial (Tarea 10); transferencias con cargos (Tarea 11); ajustes de saldo (Tarea 12); bolsillos (Tarea 13); resumen (Tarea 14); datos de prueba (Tarea 15); 522 pruebas. |
| **Documentado** | Requisitos (17 RF, 10 RNF, 15 criterios), arquitectura, modelo de datos (6 tablas), reglas de negocio, 21 decisiones (todas confirmadas), auditoría del diseño anterior, categorías por defecto, guía de continuidad, instalación y uso diario en `README.md`. |
| **Pendiente** | Ninguna tarea de la guía. Interfaz: faltan las pantallas de transferencias, ajustes y bolsillos. | La interfaz React (`frontend/`) se desarrolla en otra asignatura. |

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

### 3.10 Ajustes de saldo (Tarea 12: RF-17)

| Archivo | Qué hace |
| --- | --- |
| `app/servicios/ajustes.py` | `AjusteServicio.ajustar`: flujo 5.4 de `ARQUITECTURA.md` — bloquea la cuenta (`FOR UPDATE`), calcula el saldo, registra `AJUSTE_AUMENTO` o `AJUSTE_DISMINUCION` por la diferencia (nada si es 0). `corregir`: fecha y motivo. `ResultadoAjuste` (saldo anterior, cuenta y ajuste). |
| `app/repositorios/movimientos.py` | Nuevos `insertar_ajuste` y `corregir_ajuste`. |
| `app/rutas/ajustes.py` | `POST /api/cuentas/<id>/ajustes` (201 si hubo ajuste, 200 si no) y `PUT /api/ajustes/<id>`. |
| `app/rutas/entrada.py` | Nuevo `fecha_opcional`. |

Verificado:
- `tests/test_ajustes.py` (28 casos): CA-11 (480.000 → 473.500: `AJUSTE_DISMINUCION` de 6.500;
  ingresos y egresos sin cambio, RN-53), aumento, diferencia cero, saldo real negativo, motivo
  obligatorio, cuenta archivada y ajena, anular y reactivar (RN-54), corregir y API.
- **RN-55 con una carrera real:** otra conexión deja un ingreso de 1.000 sin confirmar y lo confirma
  medio segundo después; el ajuste espera e incluye ese ingreso (saldo anterior 1.000, ajuste de
  4.000, saldo final 5.000). **Prueba de mutación:** sin el `FOR UPDATE`, el ajuste calcula con saldo
  0 y la prueba falla.
- Servidor real (contra `financia_pruebas`): CA-11, sin diferencia (200, sin ajuste), corregir el
  monto rechazado, anular el ajuste devuelve el saldo. Datos de la verificación eliminados.
- Las pruebas dejan la base de pruebas vacía.

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-29 a P-33):
- **De un ajuste solo se corrigen la fecha y el motivo.** RN-72 permite corregir el monto de
  cualquier movimiento, pero el monto de un ajuste no lo escribe el usuario: sale de un cálculo.
  Si estaba mal, se anula y se hace otro ajuste con el saldo real correcto.
- **La fecha del ajuste es opcional**: si no se envía, es la de hoy.
- **El saldo real puede ser negativo** (por ejemplo, un sobregiro), igual que el saldo calculado (RN-14).
- **Sin diferencia, la respuesta es 200 con `"ajuste": null`** y no se registra nada (RN-51).
- **La ruta va bajo la cuenta**: `POST /api/cuentas/<id>/ajustes`.

### 3.11 Bolsillos y metas (Tarea 13: RF-08 a RF-10, RF-12)

| Archivo | Qué hace |
| --- | --- |
| `app/entidades/bolsillo.py` | `Bolsillo` (`es_meta()`: tiene monto objetivo, D-08), `ValorBolsillo`, `BolsilloConValor` (bolsillo + valor actual; `progreso_porcentaje()`, RN-48). |
| `app/repositorios/bolsillos.py` | Valor actual con `DISTINCT ON (id_bolsillo) … ORDER BY id_bolsillo, registrado_en DESC, id_bolsillo_valor DESC` (D-09), historial, insertar bolsillo y valor, editar, archivar. |
| `app/servicios/bolsillos.py` | `BolsilloServicio`: crear con su primer valor en una transacción (RN-45), editar (genérico ↔ meta), cambiar valor (RN-44; sin registro si es igual, RN-46), archivar con cualquier valor (RN-49), reactivar. |
| `app/rutas/bolsillos.py` | `GET`/`POST /api/bolsillos`, `GET`/`PUT /api/bolsillos/<id>`, `POST …/valor`, `…/archivar`, `…/reactivar`. |

Verificado:
- `tests/test_bolsillos.py` (42 casos): CA-07 (35 %, un registro más, ningún saldo ni movimiento
  cambia), CA-08, CA-09 (una transferencia no toca el bolsillo), RN-41 a RN-49, RN-06 y API.
- **Desempate del "más reciente" (D-09):** valores guardados en la misma transacción tienen la
  misma hora; la prueba confirma que el valor actual es el último. **Prueba de mutación:** sin
  `id_bolsillo_valor DESC` en el orden, el valor actual sale el primero (10 en vez de 5) y la
  prueba falla.
- Servidor real (contra `financia_pruebas`): crear meta, CA-07, CA-08, CA-09 con una transferencia
  real, historial y archivar. Datos de la verificación eliminados.
- Las pruebas dejan la base de pruebas vacía (también `bolsillo` y `bolsillo_valor`).

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-34 a P-39):
- **Un bolsillo archivado no se edita ni cambia de valor**: primero se reactiva (como cuentas y
  categorías, P-11 y P-17). Existe la acción **reactivar**; si otro bolsillo activo tiene el mismo
  nombre, se rechaza.
- **`PUT /api/bolsillos/<id>` reemplaza todos los datos**: si no se envía `monto_objetivo`, el
  bolsillo queda genérico (y pierde su fecha objetivo). La interfaz debe enviar siempre la meta
  que quiere conservar.
- **El progreso viaja como porcentaje con 2 decimales** (`"35.00"`), o `null` si no es meta.
- **`GET /api/bolsillos/<id>` trae el historial completo**, del más reciente al más antiguo.
- **Cambiar al mismo valor responde 200 con `"registrado": false`** (201 si se agregó un registro).
- **La fecha objetivo puede estar en el pasado**: los documentos no lo limitan.

### 3.12 Resumen financiero e indicadores (Tarea 14: RF-13, RF-15)

| Archivo | Qué hace |
| --- | --- |
| `app/repositorios/resumen.py` | Dos consultas de solo lectura: totales del periodo por tipo (`GROUP BY tipo`) y por categoría, con su raíz (`LEFT JOIN categoria raiz` + `COALESCE`). |
| `app/servicios/resumen.py` | `ResumenServicio.indicadores` (saldo total de cuentas activas, total reservado de bolsillos activos, disponible y aviso) reutilizando los cálculos de cuentas y bolsillos; `periodo` (ingresos, egresos, balance, ajustes aparte, categorías consolidadas). |
| `app/rutas/resumen.py` | `GET /api/resumen?desde=&hasta=` → `{indicadores, periodo}`. |

Verificado:
- `tests/test_resumen.py` (23 casos): CA-10 (disponible −50.000 con aviso; después se sigue
  reservando y gastando), CA-12 (Alimentación 50.000 = 20.000 directos + Mercado 30.000), RN-60 a
  RN-64, RN-53, RN-27 (la suma de las raíces es igual al total de egresos) y, desde el resumen,
  CA-01, CA-02, CA-11 y CA-14.
- **Pruebas de mutación:** sin la consolidación en la raíz fallan 2 pruebas; sin el filtro
  `estado = 'VIGENTE'` falla 1. Con el código correcto, pasan todas.
- Servidor real (contra `financia_pruebas`) con ingresos, egresos en raíz y subcategoría, una
  transferencia con cargo, un ajuste y un bolsillo: indicadores (saldo 299.000, reservado 350.000,
  disponible −51.000 con aviso), egresos 50.400 (incluye el cargo, no la transferencia), ajuste
  aparte (600) y Alimentación consolidada. Datos de la verificación eliminados.
- Las pruebas dejan la base de pruebas vacía.

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-40 a P-44):
- **Una sola ruta** (`GET /api/resumen`) devuelve los indicadores y el resumen del periodo.
- **Sin fechas, el periodo es el mes actual completo** (del día 1 al último día).
- **Los indicadores son del momento actual**: no dependen del periodo elegido.
- **En los totales por categoría solo aparecen las que tienen movimientos en el periodo**,
  ordenadas de mayor a menor total, con su parte **"directo"** (movimientos asignados a la raíz
  misma) separada de sus subcategorías.
- **El balance es ingresos − egresos**; los ajustes se muestran aparte y no entran (RN-53).

### 3.13 Datos de prueba y cierre (Tarea 15)

| Archivo | Qué hace |
| --- | --- |
| `db/semillas/datos_prueba.sql` | Tres usuarios ficticios con los escenarios de CA-01 a CA-15, en SQL a mano (solo `INSERT`, dentro de `BEGIN … COMMIT`). El encabezado dice qué debe verse en cada cuenta, bolsillo y resumen. |
| `scripts/cargar_datos_prueba.py` | Lo carga en la base de desarrollo en una transacción; si los usuarios ya existen, no hace nada. |
| `tests/test_datos_prueba.py` | Carga el archivo dentro de una transacción, comprueba con los servicios cada valor del encabezado y los rechazos sobre esos datos, y lo deshace. |
| `README.md` | Nueva sección de rutas de la API y cómo cargar los datos de demostración. |
| `tests/LEEME.md` | Matriz: qué pruebas cubren cada criterio de aceptación. |

Verificado:
- `tests/test_datos_prueba.py` (16 casos): el archivo se carga con el rol `financia_app`; saldos,
  indicadores y resumen de Ana; CA-02, CA-04, CA-07, CA-09 a CA-15 con datos; CA-03, CA-05, CA-06,
  CA-08 y CA-15 rechazados sobre esos datos; inicio de sesión con la contraseña de demostración; la
  lista de categorías del archivo es igual a la de `categorias_por_defecto.py`.
- `cargar_datos_prueba.py` ejecutado dos veces sobre `financia_pruebas`: la primera carga, la
  segunda no hace nada. Con el servidor real, Ana inicia sesión y ve saldo total 1.032.700,
  reservado 350.000, egresos de noviembre 90.800, ajustes 6.500 aparte, y archivar Efectivo es
  rechazado (CA-15). Después se borraron esos datos con `financia_admin`.
- **No se cargaron datos en la base `financia`**: eso lo decide el estudiante (comando en `README.md`).

Decisiones tomadas en esta tarea, **confirmadas por el estudiante el 22/11/2026** (sección 6, P-45 a P-48):
- **Contraseña de demostración fija** (`demo-financia-2026`), escrita en el README y en el
  encabezado del archivo, con su hash en el SQL. Es ficticia y solo para la base local; permite
  iniciar sesión en la sustentación.
- **Tres usuarios**: Ana (casi todos los criterios, cada uno en su propia cuenta para que se
  vean por separado), Beto ("el otro usuario" de CA-06) y Carla (CA-09 y CA-10, que necesitan
  totales exactos).
- **El archivo guarda el estado final** de cada escenario (por ejemplo, Daviplata ya archivada y
  Mascotas ya desactivada con su movimiento anterior). Los criterios que son rechazos no dejan
  datos: se prueban con la API sobre estos datos.
- **La lista de categorías por defecto está en dos lugares** (`categorias_por_defecto.py` y el
  SQL); una prueba avisa si dejan de coincidir.

### 3.14 Interfaz React, paso 1: base, sesión y resumen

Elecciones del estudiante (22/11/2026): **React Router y CSS propio, sin librerías de
componentes**; empezar por la base, la sesión y el resumen, y seguir con una pantalla por paso.

| Pieza | Qué hace |
| --- | --- |
| `frontend/vite.config.ts` | Proxy de `/api` hacia Flask: mismo origen, la cookie funciona sin CORS. |
| `frontend/src/api/cliente.ts` | Todas las peticiones: JSON, cookie, encabezado CSRF y `ErrorApi` con el mensaje de la API. |
| `frontend/src/sesion/ContextoSesion.tsx` | Sesión en un contexto de React; se consulta al servidor al abrir la página. |
| `frontend/src/paginas/` | Iniciar sesión, registro y resumen. |
| `frontend/src/util/formato.ts` | Dinero y fechas sin convertir a número (14 pruebas con Vitest). |

Versiones instaladas y fijadas en `frontend/package.json`: React 19.3.1, React Router 8.5.2,
Vite 8.3.8, TypeScript 7.0.2, Vitest 5.1.1 (Node 24.22.1).

Verificado en el navegador, contra la API real y la base `financia` con los datos de demostración:
- Sin sesión, `/` lleva a "Iniciar sesión". Contraseña equivocada: muestra "Correo o contraseña
  incorrectos.". Con la contraseña de Ana: el resumen muestra saldo 1.032.700, reservado 350.000,
  egresos 90.800, balance −40.800 (en rojo), ajustes aparte y Alimentación con Mercado.
- Cambiar a octubre: todo en 0 y "No hay movimientos en este periodo".
- Recargar la página mantiene la sesión (cookie); "Cerrar sesión" vuelve a "Iniciar sesión".
- Registro con un correo existente (en mayúsculas): rechazado con el mensaje de la API; no se creó
  ningún usuario en `financia`.
- Vista de celular (375 px) sin desbordamiento; con Carla se ve el aviso de CA-10 (−50.000).
- `npm run build` sin errores de tipos; la consola solo muestra los 401/400 esperados.

### 3.15 Interfaz React, paso 2: cuentas

| Pieza | Qué hace |
| --- | --- |
| `frontend/src/paginas/Cuentas.tsx` | Lista de cuentas con saldo, crear, editar, archivar y reactivar; casilla para ver también las archivadas. |
| `frontend/src/api/cuentas.ts` | Una función por ruta de `/api/cuentas`. |
| `frontend/src/componentes/CampoDinero.tsx` | Campo de dinero reutilizable: texto (no número), muestra cómo quedó el monto ("$ 1.500.000,50"). |
| `frontend/src/util/formato.ts` | Nuevas: `dineroParaEnviar` ("150000,50" → "150000.50"), `dineroParaCampo` y `esDineroValido`. 29 pruebas con Vitest. |
| `frontend/vite.config.ts` | El destino del proxy se puede cambiar con `FINANCIA_API` (por defecto, el puerto 5000). |

Cómo se escribe el dinero: solo números, centavos con coma o punto, **sin puntos de miles**
("1.000" sería ambiguo). Si no cumple, el formulario lo dice antes de enviar; las demás reglas
(máximo, RN-13) las revisa la API.

Verificado en el navegador con Ana, contra una API conectada a `financia_pruebas` (con los datos
de demostración, que después se borraron: la base de pruebas quedó vacía; `financia` no se tocó):
- Las 4 cuentas activas suman 1.032.700, igual que el resumen.
- Archivar Nequi (saldo 229.200): rechazado con el mensaje de la API (RN-12, CA-15).
- Crear "Daviplata" con saldo "1500000,5": se ve $ 1.500.000,50. Con "1.500.000": el formulario pide
  escribirlo sin puntos.
- Cambiar el saldo inicial de Nequi (tiene movimientos): rechazado por RN-13. Renombrarla a
  "Bancolombia": "Ya tiene una cuenta activa con ese nombre."; a "Nequi personal": guardado.
- Daviplata: saldo inicial a 0, archivar, verla con "Mostrar archivadas" y reactivarla. Reactivar la
  otra Daviplata archivada de los datos de demostración: rechazado (nombre repetido entre activas).
- Con un egreso de 25.000 en Daviplata: saldo −$ 25.000 en rojo y aviso de RN-14.
- Vista de celular (375 px) sin desbordamiento.

### 3.16 Interfaz React, paso 3: categorías

| Pieza | Qué hace |
| --- | --- |
| `frontend/src/paginas/Categorias.tsx` | Pestañas Egresos / Ingresos; cada raíz en una tarjeta con sus subcategorías. Crear raíz y subcategoría, renombrar, desactivar y reactivar; casilla para ver las desactivadas. |
| `frontend/src/api/categorias.ts` | Una función por ruta de `/api/categorias`. La subcategoría se crea sin tipo: lo toma del padre (RN-23). |

Solo se ofrece cambiar el **nombre** (RN-22). Antes de desactivar una raíz con subcategorías
activas, la pantalla pide confirmación, porque al reactivar la raíz las subcategorías no vuelven
solas (así funciona `CategoriaServicio.reactivar`).

Verificado en el navegador con Ana, contra una API conectada a `financia_pruebas` (los datos de
demostración se borraron al terminar; `financia` no se tocó):
- Egresos muestra las 10 raíces con sus subcategorías; Ingresos, las 4 de ingreso.
- Crear "Mascotas": aparece. Crear "alimentación": "Ya existe una categoría activa con ese nombre en
  el mismo nivel." (RN-24, sin importar mayúsculas). Subcategoría "Veterinario": agregada;
  "Mercado" repetida en Alimentación: rechazada.
- Desactivar Alimentación: pide confirmación (3 subcategorías); con "No" no cambia nada; con "Sí",
  aviso "Se desactivó "Alimentación" y 3 subcategorías".
- Reactivar Mercado antes que su padre: "Primero reactive la categoría padre.". Reactivar
  Alimentación: sus subcategorías siguen desactivadas, y Mercado se reactiva después.
- Renombrar a "Salud": rechazado; a "Mascotas y animales": guardado. Luego la "Mascotas"
  desactivada de los datos de demostración se pudo reactivar.
- Vista de celular (375 px) sin desbordamiento.

### 3.17 Interfaz React, paso 4: movimientos

| Pieza | Qué hace |
| --- | --- |
| `frontend/src/paginas/Movimientos.tsx` | Historial con filtros (fechas, cuenta, tipo, categoría con sus subcategorías, estado); registrar ingresos y egresos; corregir, anular y reactivar. |
| `frontend/src/api/movimientos.ts` | Una función por ruta de `/api/movimientos`; solo envía los filtros que tienen valor. |
| `frontend/src/componentes/SelectorCategoria.tsx` | Lista de categorías reutilizable ("Alimentación › Mercado"); la raíz también se puede elegir. |
| `frontend/src/util/movimientos.ts` | Monto con signo según el tipo, nombre del tipo ("Cargo de transferencia") y qué botones ofrecer. 14 pruebas nuevas (43 en total). |

El historial muestra todos los tipos y también los anulados (CA-13, tachados). Los botones siguen lo
que permite la API en esta ruta: corregir solo ingresos y egresos vigentes que no sean cargos;
anular y reactivar todo menos las transferencias, que van con sus cargos (RN-38) en su propia
pantalla. El formulario ofrece solo cuentas y categorías activas; al corregir también muestra las
que el movimiento ya tiene, porque la API conserva una categoría desactivada si no cambia.

Verificado en el navegador con Ana, contra una API conectada a `financia_pruebas` (los datos de
demostración se borraron al terminar; `financia` no se tocó):
- Historial: 10 movimientos de todos los tipos, con los anulados visibles; los montos con signo.
- Registrar un egreso de "25000,5" en Nequi › Mercado: aparece primero como −$ 25.000,50; la fecha
  viene con el día de hoy. En la pestaña Ingreso solo aparecen categorías de ingreso.
- Corregir: el formulario trae los datos y no deja cambiar el tipo; a 26.000 y Restaurantes, guardado.
- Anular: queda tachado y sin "Corregir"; reactivar lo devuelve.
- Reactivar el cargo de una transferencia anulada: "Este cargo pertenece a una transferencia
  anulada. Reactive primero la transferencia."
- Corregir "Veterinario" (categoría Mascotas desactivada después): la muestra como
  "(desactivada)" y la API lo acepta porque la categoría no cambia.
- Filtro Egreso + Alimentación: incluye Mercado, Restaurantes y Alimentación directo. Fechas al
  revés: "La fecha inicial no puede ser posterior a la fecha final."
- El resumen refleja el egreso nuevo: egresos 116.800 y saldo total 1.006.700 (26.000 más y menos).
- Vista de celular (375 px) sin desbordamiento.

## 4. Lo que NO existe todavía

- Las demás pantallas de la interfaz: transferencias, ajustes y bolsillos. La API ya ofrece todo lo que necesitan (sección de rutas en `README.md`).
- Lo aplazado por decisión del proyecto (`REQUISITOS.md`, sección 3): facturas, Gmail,
  presupuestos, recurrentes, tarjetas, renta, notificaciones, auditoría, varias categorías.
- El repositorio Git no tiene remoto (no se ha subido a GitHub).
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
| 12 | Ajustes de saldo | **Hecho: 28 pruebas; servidor probado** | RF-17 |
| 13 | Bolsillos, metas e historial | **Hecho: 42 pruebas; servidor probado** | RF-08 a RF-10, RF-12 |
| 14 | Resumen financiero e indicadores | **Hecho: 23 pruebas; servidor probado** | RF-13, RF-15 |
| 15 | Datos de prueba y pruebas de CA-01 a CA-15 | **Hecho: 16 pruebas; cargador y servidor probados** | `REQUISITOS.md`, sección 4 |

**Siguiente paso recomendado:** cargar los datos de demostración en `financia` para la sustentación y, si se quiere, subir el repositorio a GitHub. La versión 1 de la API está completa.

## 6. Decisiones confirmadas por el estudiante (17 y 22 de noviembre de 2026)

Ya no hay decisiones abiertas: todas (P-1 a P-48) están confirmadas.

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
| P-29 | ¿Qué se corrige de un ajuste? (22/11) | Solo la fecha y el motivo; si el monto estaba mal, se anula y se ajusta de nuevo. Precisa RN-72 para los ajustes. | `AjusteServicio.corregir` |
| P-30 | ¿La fecha del ajuste es obligatoria? (22/11) | No: por defecto, la de hoy. | `AjusteServicio.ajustar` |
| P-31 | ¿El saldo real puede ser negativo? (22/11) | Sí. | `AjusteServicio.ajustar` |
| P-32 | ¿Qué responde un ajuste sin diferencia? (22/11) | 200 con `"ajuste": null`; no se registra nada. | `POST /api/cuentas/<id>/ajustes` |
| P-33 | ¿Dónde va la ruta del ajuste? (22/11) | Bajo la cuenta: `POST /api/cuentas/<id>/ajustes`. | `app/rutas/ajustes.py` |
| P-34 | ¿Un bolsillo archivado se edita o cambia de valor? (22/11) | No: primero se reactiva. Existe reactivar (rechazado si el nombre está ocupado). | `BolsilloServicio` |
| P-35 | ¿`PUT /api/bolsillos/<id>` reemplaza todo? (22/11) | Sí: sin `monto_objetivo`, queda genérico y sin fecha objetivo. | `app/rutas/bolsillos.py` |
| P-36 | ¿Cómo viaja el progreso? (22/11) | Porcentaje con 2 decimales como texto (`"35.00"`), o `null` si no es meta. | `BolsilloConValor` |
| P-37 | ¿El detalle trae el historial? (22/11) | Sí, completo, del más reciente al más antiguo. | `GET /api/bolsillos/<id>` |
| P-38 | ¿Qué responde cambiar al mismo valor? (22/11) | 200 con `"registrado": false` (201 si se agrega un registro). | `POST /api/bolsillos/<id>/valor` |
| P-39 | ¿La fecha objetivo puede estar en el pasado? (22/11) | Sí. | `BolsilloServicio` |
| P-40 | ¿Una ruta o varias para el resumen? (22/11) | Una: `GET /api/resumen` con indicadores y periodo. | `app/rutas/resumen.py` |
| P-41 | ¿Periodo por defecto? (22/11) | El mes actual completo. | `ResumenServicio.periodo` |
| P-42 | ¿Los indicadores dependen del periodo? (22/11) | No: son del momento actual. | `ResumenServicio.indicadores` |
| P-43 | ¿Qué categorías aparecen en el resumen? (22/11) | Solo las que tienen movimientos en el periodo, de mayor a menor, con su parte "directo" separada de sus subcategorías. | `ResumenServicio` |
| P-44 | ¿El balance incluye los ajustes? (22/11) | No: ingresos − egresos; los ajustes van aparte (RN-53). | `ResumenPeriodo.balance` |
| P-45 | ¿Contraseña de los usuarios de demostración? (22/11) | Fija y ficticia (`demo-financia-2026`), solo para la base local. | `db/semillas/datos_prueba.sql` |
| P-46 | ¿Cuántos usuarios de demostración? (22/11) | Tres: Ana (casi todos los criterios), Beto (CA-06) y Carla (CA-09, CA-10). | `db/semillas/datos_prueba.sql` |
| P-47 | ¿Qué guarda el archivo de datos de prueba? (22/11) | El estado final de cada escenario; los rechazos se prueban con la API sobre esos datos. | `db/semillas/datos_prueba.sql` |
| P-48 | ¿La lista de categorías por defecto en dos lugares? (22/11) | Sí (Python y SQL), con una prueba que avisa si dejan de coincidir. | `tests/test_datos_prueba.py` |

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
| 2026-11-22 | Tarea 12: ajustes de saldo (`AjusteServicio` con `FOR UPDATE`, rutas `/api/cuentas/<id>/ajustes` y `/api/ajustes/<id>`); `tests/test_ajustes.py` con CA-11 y carrera real de RN-55 con prueba de mutación. Servidor probado. **441 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-29 a P-33 (ajustes: solo fecha y motivo se corrigen, fecha por defecto hoy, saldo real negativo, 200 sin diferencia, ruta bajo la cuenta). |
| 2026-11-22 | Tarea 13: bolsillos y metas (`Bolsillo`, `BolsilloConValor`, `BolsilloRepositorio` con `DISTINCT ON`, `BolsilloServicio`, rutas `/api/bolsillos`); `tests/test_bolsillos.py` con CA-07, CA-08, CA-09 y prueba de mutación del desempate. Servidor probado. **483 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-34 a P-39 (bolsillos: archivado no se edita, PUT reemplaza todo, progreso en porcentaje, detalle con historial, 200 sin cambio, fecha objetivo libre). |
| 2026-11-22 | Tarea 14: resumen financiero e indicadores (`ResumenRepositorio`, `ResumenServicio`, `GET /api/resumen`); `tests/test_resumen.py` con CA-10 y CA-12 y pruebas de mutación. Servidor probado. **506 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-40 a P-44 (resumen: una ruta, mes actual por defecto, indicadores del momento, solo categorías con movimientos, balance sin ajustes). |
| 2026-11-22 | Tarea 15: datos de prueba (`db/semillas/datos_prueba.sql`, `scripts/cargar_datos_prueba.py`, `tests/test_datos_prueba.py`), matriz de criterios en `tests/LEEME.md` y rutas en `README.md`. **Versión 1 de la API completa: 522 pruebas pasan.** |
| 2026-11-22 | Confirmadas P-45 a P-48 (datos de prueba). No quedan decisiones abiertas. |
| 2026-11-22 | Interfaz React, paso 1 (`frontend/`): Vite + React + TypeScript, cliente de la API, sesión (registro, inicio y cierre) y pantalla de resumen. Probada en el navegador contra la API real. |
| 2026-11-22 | Interfaz React, paso 2: pantalla de cuentas (crear, editar, archivar, reactivar) y campo de dinero reutilizable. Probada en el navegador contra la base de pruebas. |
| 2026-11-22 | Interfaz React, paso 3: pantalla de categorías (árbol por tipo, crear, renombrar, desactivar y reactivar). Probada en el navegador contra la base de pruebas. |
| 2026-11-22 | Interfaz React, paso 4: pantalla de movimientos (historial con filtros, registrar, corregir, anular y reactivar). Probada en el navegador contra la base de pruebas. |
