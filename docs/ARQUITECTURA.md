# Arquitectura — FINANCIA+ versión 1

> Nada de lo descrito aquí está implementado todavía. Este documento define cómo debe
> construirse. El estado real está en `ESTADO_PROYECTO.md`.

## 1. Visión general

Dos aplicaciones: una **API** en Flask, orientada a objetos y por capas, y una **interfaz**
en React + Vite + TypeScript que la consume (la interfaz se desarrolla en otra asignatura y
vive en la carpeta `frontend/`). La base de datos, los repositorios y los servicios no
dependen de la tecnología de la interfaz.

```
Interfaz React + Vite + TypeScript (frontend/)
        │  HTTP + JSON  (en desarrollo, Vite reenvía /api a Flask: mismo origen)
        ▼
┌──────────────────────────────────────────────┐
│ API Flask (app/)                             │
│                                              │
│  rutas/         reciben la petición JSON,    │
│                 validan su forma, llaman a   │
│                 un servicio y responden JSON │
│        │                                     │
│        ▼                                     │
│  servicios/     reglas de negocio y          │
│                 TRANSACCIONES                │
│        │                                     │
│        ▼                                     │
│  repositorios/  SQL escrito a mano,          │
│                 parametrizado                │
└────────┬─────────────────────────────────────┘
         │  psycopg
         ▼
   PostgreSQL  (6 tablas, restricciones declarativas, sin triggers)
```

## 2. Tecnologías

| Pieza | Elección | Por qué |
| --- | --- | --- |
| Base de datos | PostgreSQL | Definido por el curso. Ofrece FK compuestas, CHECK, índices únicos parciales y transacciones. |
| Lenguaje | Python 3 | Legible para quien empieza. |
| Framework web | Flask | Pequeño: se entiende completo. |
| Acceso a datos | `psycopg` (versión 3) con SQL escrito a mano | El curso exige ver y explicar el SQL. Sin ORM. |
| Paradigma | Programación orientada a objetos por capas | Lo exige otra asignatura; encaja con el diagrama de clases del proyecto. Ver sección 3.1. |
| Interfaz | React + Vite + TypeScript, en `frontend/`, que consume la API JSON | Decisión del estudiante (D-21). Se desarrolla en otra asignatura. |
| Migraciones | Archivos `.sql` numerados + un script pequeño que los aplica en orden | SQL legible y versionado, sin herramienta que lo genere. |
| Pruebas | `pytest` contra una base PostgreSQL de pruebas | Las reglas importantes viven en la base; hay que probarlas contra una base real. |
| Configuración | Variables de entorno (archivo `.env` local, no versionado) | Secretos fuera del código. |

Stack confirmado por el estudiante (D-18, D-19, D-21): Flask como API JSON, `psycopg` con
SQL a mano, POO por capas, migraciones con script propio y React + Vite + TypeScript como interfaz.

## 3. Responsabilidad de cada capa

| Capa | Hace | No hace |
| --- | --- | --- |
| `app/rutas/` | Funciones de Flask (blueprints). Reciben JSON; exigen sesión; convierten y validan la **forma** de los datos (¿es un número?, ¿es una fecha?); llaman a **un** método de servicio; responden JSON con el resultado o el error. | No contienen reglas de negocio ni SQL. No abren transacciones. |
| `app/servicios/` | Clases (`CuentaServicio`, `TransferenciaServicio`...). Aplican las reglas de `REGLAS_NEGOCIO.md`; abren y cierran la transacción; usan los repositorios; lanzan `ErrorNegocio` con mensaje claro. | No conocen HTTP ni JSON. No contienen SQL. |
| `app/repositorios/` | Clases (`CuentaRepositorio`...) que reciben la conexión en el constructor y contienen el SQL. Cada método hace una consulta, **recibe siempre `id_usuario`** y devuelve entidades. | No deciden reglas. No hacen COMMIT ni ROLLBACK. |
| `app/entidades/` | `dataclasses` que representan una fila (`Cuenta`, `Movimiento`...) con métodos de cálculo simples (`Bolsillo.es_meta()`). | No acceden a la base. |
| Base de datos | Hace cumplir lo declarativo: propiedad, tipos, formas, unicidad, rangos. | No tiene triggers ni funciones de negocio en la versión 1. |

Regla práctica: **una acción del usuario = un método de servicio = una transacción.**

### 3.1 Orientación a objetos

| Elemento | Forma | Ejemplo |
| --- | --- | --- |
| Entidades | `@dataclass(frozen=True)`; una clase por tabla. `Movimiento` es **una sola clase** con su atributo `tipo` (sin herencia), igual que la tabla. | `Cuenta(id_cuenta, id_usuario, nombre, tipo, saldo_inicial, activa, creado_en)` |
| Enumeraciones | `enum.StrEnum` para los valores fijos de los CHECK. | `TipoMovimiento.TRANSFERENCIA` |
| Repositorios | Una clase por tabla; reciben la conexión en `__init__`. | `CuentaRepositorio(con).obtener(id_usuario, id_cuenta)` |
| Servicios | Una clase por módulo; reciben la conexión y crean sus repositorios. Cada método público abre su transacción. | `TransferenciaServicio(con).registrar(id_usuario, datos)` |
| Errores | `ErrorNegocio` (mensaje para el usuario) y `NoEncontrado` (404). | |
| Dinero | `Decimal` en entidades y servicios; en JSON viaja como texto (`"200000.00"`). | |

Sin herencia entre entidades, sin clases abstractas "por si acaso" y sin ORM: simple gana a ingenioso.

## 4. Módulos funcionales

Un archivo por módulo en cada capa (por ejemplo `rutas/cuentas.py`, `servicios/cuentas.py`
con `CuentaServicio`, `repositorios/cuentas.py` con `CuentaRepositorio`). Todas las rutas de
la API empiezan por `/api/` (por ejemplo `GET /api/cuentas`).

| Módulo | Requisitos | Tablas |
| --- | --- | --- |
| `autenticacion` | RF-01 | `usuario` |
| `cuentas` | RF-02, RF-11, RF-17 | `cuenta`, `movimiento` |
| `categorias` | RF-03 | `categoria` |
| `movimientos` | RF-04, RF-05, RF-14, RF-16 | `movimiento` |
| `transferencias` | RF-06, RF-07 | `movimiento` |
| `bolsillos` | RF-08, RF-09, RF-10, RF-12 | `bolsillo`, `bolsillo_valor` |
| `resumen` | RF-13, RF-15 | todas (solo lectura) |

## 5. Flujos principales

### 5.1 Ingreso o egreso
1. La ruta lee cuenta, monto, categoría, fecha y descripción.
2. El servicio verifica que la cuenta y la categoría estén activas (RN-12, RN-25).
3. El repositorio inserta **una fila** en `movimiento`.
4. La base rechaza, si aplica: cuenta o categoría de otro usuario, categoría de tipo distinto, monto ≤ 0.

### 5.2 Transferencia con cargos
Todo dentro de una transacción (RN-37):
1. Insertar la fila TRANSFERENCIA (origen, destino, monto, fecha).
2. Por cada cargo: insertar una fila EGRESO con `id_transferencia`, la misma cuenta de origen, la misma fecha, su monto y su categoría.
3. COMMIT. Si cualquier paso falla, ROLLBACK: no queda nada.

La transferencia nunca queda "a medias" porque origen y destino están en **la misma fila**.
Lo único que puede fallar por separado son los cargos, y la transacción lo cubre.

### 5.3 Cambio de valor de un bolsillo
1. El servicio lee el valor actual.
2. Si el valor nuevo es igual, no hace nada (RN-46).
3. Si es distinto, inserta una fila en `bolsillo_valor`. No toca cuentas ni movimientos.

Crear un bolsillo inserta `bolsillo` y su primer `bolsillo_valor` en la misma transacción (RN-45).

### 5.4 Ajuste de saldo
Dentro de una transacción (RN-55):
1. Bloquear la fila de la cuenta (`SELECT ... FOR UPDATE`).
2. Calcular el saldo actual.
3. Diferencia = saldo real indicado − saldo calculado.
4. Si es distinta de cero, insertar AJUSTE_AUMENTO o AJUSTE_DISMINUCION por el valor absoluto, con el motivo.
5. COMMIT.

### 5.5 Anulación
- Movimiento simple: `estado = 'ANULADO'`.
- Transferencia: en una transacción, anular la transferencia y todos sus cargos vigentes (RN-38).

## 6. Seguridad

| Medida | Detalle |
| --- | --- |
| Contraseñas | Hash con las utilidades de Werkzeug (incluidas con Flask). Nunca texto plano ni en registros. |
| Sesión | Cookie firmada de Flask con `SECRET_KEY` tomada del entorno. `HttpOnly` y `SameSite=Lax`. La interfaz y la API comparten origen (en desarrollo, el proxy de Vite reenvía `/api` a Flask), así que no hace falta CORS ni tokens en el navegador. |
| Control de propietario | El `id_usuario` sale de la sesión. Todas las consultas filtran por él. Un recurso ajeno responde 404. |
| Segunda barrera | FK compuestas de propiedad en la base (ver `MODELO_DATOS.md`). |
| Inyección SQL | Solo consultas parametrizadas de `psycopg` (`%s` o `%(nombre)s`). Prohibido armar SQL con f-strings o concatenación. |
| CSRF | Las peticiones que modifican datos solo aceptan `Content-Type: application/json` y exigen el encabezado `X-Requested-With: financia`; un formulario de otro sitio no puede enviar ninguno de los dos. Junto con `SameSite=Lax`, cubre el riesgo. |
| Secretos | En `.env`, que no se versiona. `.env.example` solo trae nombres y valores falsos. |
| Permisos en la base | La aplicación se conecta con un rol propio, que no es dueño de las tablas y **no tiene permiso `DELETE`**, ni `UPDATE` sobre `bolsillo_valor`. Las migraciones se ejecutan con otro rol. |

## 7. Riesgos de concurrencia y operaciones parciales

| Riesgo | Ejemplo | Mitigación |
| --- | --- | --- |
| Operación parcial | Se guarda la transferencia y falla el cargo. | Una transacción por acción (sección 5.2). |
| Doble envío del formulario | Doble clic en "Guardar" crea dos egresos iguales. | La interfaz deshabilita el botón mientras espera la respuesta. No se agrega control en la base en la versión 1; queda documentado como riesgo aceptado. |
| Ajuste con saldo desactualizado | Mientras se calcula el ajuste, otra pestaña registra un egreso. | Bloqueo de la fila de la cuenta durante el ajuste (sección 5.4). |
| Dos cambios simultáneos de un bolsillo | Dos pestañas escriben valores distintos. | Se insertan los dos registros; gana el más reciente. Es el comportamiento esperado de "edición directa". |
| Anulación incompleta | Se anula la transferencia pero no su cargo. | Una transacción (sección 5.5). |
| Corrección que rompe una relación | Cambiar la cuenta de origen de una transferencia con cargos. | No se permite (RN-72); la FK del cargo además lo impide. |
| Saldos negativos | Se registra un egreso mayor que el saldo. | No se bloquea: el registro es manual y puede faltar un ingreso. Se muestra aviso (RN-14). |

## 8. Cómo crecerá el sistema

Cada funcionalidad aplazada llega como: una migración nueva (sus tablas) + un archivo por capa.
Ejemplos: `presupuesto` (tabla nueva que apunta a `categoria`), `recurrente` (tabla nueva que
genera movimientos), facturas (tablas nuevas que apuntan a `movimiento`). Ninguna requiere
rehacer las seis tablas actuales. La evolución a varias categorías por movimiento está
descrita en `MODELO_DATOS.md`, sección 7.
