# FINANCIA+

Administrador de finanzas personales con **registro manual**. Proyecto del curso Base de
Datos 1 (UTP, Colombia).

> **Estado: base de datos creada, migrada (`0001` y `0002`) y probada; esqueleto de la API
> Flask funcionando (`GET /api/salud`). Todavía no hay módulos de negocio (autenticación,
> cuentas, movimientos...) ni interfaz.** El detalle está en
> [`docs/ESTADO_PROYECTO.md`](docs/ESTADO_PROYECTO.md).

## Qué hace (versión 1)

- El usuario crea sus **cuentas** (Nequi, Nubank, Efectivo...) y registra a mano sus
  **ingresos**, **egresos** y **transferencias**. El saldo de cada cuenta se calcula.
- Una transferencia puede llevar **cargos** (4×1.000, comisiones), que cuentan como gasto.
- Cada ingreso o egreso tiene **una categoría** (con subcategorías).
- Los **bolsillos** son reservas virtuales, independientes de las cuentas. El usuario escribe
  directamente cuánto quiere tener reservado; cada cambio queda en un historial. Un bolsillo
  con monto objetivo es una **meta** y muestra su progreso.
- Indicadores: saldo total de cuentas, total reservado y **disponible no reservado**.
- Si el saldo calculado no coincide con el del banco, se registra un **ajuste de saldo**.

No hay conexión con bancos. Quedan aplazados: facturas, Gmail, tarjetas de crédito,
presupuestos, recurrentes, informes tributarios, notificaciones y auditoría avanzada.

## Tecnología

Python + Flask como API JSON, programada con **orientación a objetos** por capas; PostgreSQL;
`psycopg` con SQL escrito a mano. El esquema se define con archivos SQL numerados
(migraciones), sin ORM. La interfaz es una aplicación aparte en React + Vite + TypeScript
(carpeta `frontend/`, se desarrolla en otra asignatura).

## Organización

```
financia-plus/
├── README.md              Este archivo
├── .env.example           Variables de entorno necesarias (valores de ejemplo)
├── .gitignore
├── requirements.txt       Dependencias con las versiones probadas
├── pytest.ini             Configuración de las pruebas
├── app/                   API FLASK, orientada a objetos
│   ├── __init__.py        Fábrica de la aplicación (create_app)
│   ├── config.py          Lee la configuración de .env
│   ├── bd.py              Conexión con PostgreSQL y transacciones
│   ├── errores.py         ErrorNegocio, NoEncontrado y su conversión a JSON
│   ├── csrf.py            Protección CSRF de las peticiones que modifican datos
│   ├── entidades/         Clases de datos (una por tabla)
│   ├── rutas/             Reciben peticiones JSON bajo /api/ y responden JSON
│   ├── servicios/         Reglas de negocio y transacciones
│   └── repositorios/      SQL escrito a mano
├── db/                    BASE DE DATOS
│   ├── migraciones/       Archivos .sql numerados que crean y cambian el esquema
│   ├── semillas/          Datos iniciales (categorías por defecto) y de prueba
│   └── consultas/         Consultas de referencia para la sustentación
├── frontend/              INTERFAZ React + Vite + TypeScript (otra asignatura, pendiente)
├── config/                Configuración por entorno (pendiente)
├── scripts/               Utilidades (aplicar migraciones, cargar datos)
├── tests/                 Pruebas automáticas
└── docs/                  DOCUMENTACIÓN
    ├── REQUISITOS.md               Requisitos y criterios de aceptación
    ├── ARQUITECTURA.md             Capas, flujos, seguridad, concurrencia
    ├── MODELO_DATOS.md             Las 6 tablas, relaciones y diagrama E-R
    ├── REGLAS_NEGOCIO.md           Reglas RN-xx con ejemplos
    ├── DECISIONES_ARQUITECTURA.md  Qué se decidió y por qué
    ├── AUDITORIA_DISENO_ANTERIOR.md  Qué se conservó y qué se descartó del diseño de 26 tablas
    ├── ESTADO_PROYECTO.md          Qué está hecho, qué falta, qué hay que confirmar
    └── GUIA_CONTINUIDAD_OPUS.md    Instrucciones para continuar el desarrollo
```

Cada carpeta de trabajo tiene un `LEEME.md` que explica qué va ahí y en qué estado está.

## Por dónde empezar

1. Lee `docs/ESTADO_PROYECTO.md`.
2. Sigue las tareas de `docs/GUIA_CONTINUIDAD_OPUS.md`, en orden.

## Instalación (Windows)

Requisitos: Windows con PowerShell. El script instala con `winget` lo que falte (Python 3.13,
Git y PostgreSQL 17), crea el entorno virtual, el archivo `.env` con claves aleatorias, los
roles `financia_admin` (dueño de las tablas) y `financia_app` (el de la aplicación, sin
permiso DELETE), las bases `financia` y `financia_pruebas`, aplica las migraciones y ejecuta
las pruebas. Pide la contraseña del usuario `postgres` sin mostrarla y no la guarda.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\preparar_windows.ps1
```

Si el entorno virtual deja de funcionar (por ejemplo, al mover la carpeta), se vuelve a crear:

```powershell
py -3.13 -m venv --clear .venv; .venv\Scripts\python -m pip install -r requirements.txt
```

## Uso diario

Aplicar migraciones nuevas (base principal y base de pruebas):

```powershell
.venv\Scripts\python scripts\migrar.py; .venv\Scripts\python scripts\migrar.py --variable DATABASE_URL_PRUEBAS
```

Ejecutar las pruebas:

```powershell
.venv\Scripts\python -m pytest tests -q
```

Arrancar la API (queda en http://127.0.0.1:5000; se detiene con Ctrl+C):

```powershell
.venv\Scripts\flask --app app run --debug
```

Comprobar que responde: abrir http://127.0.0.1:5000/api/salud debe mostrar `{"bd": "ok"}`.
