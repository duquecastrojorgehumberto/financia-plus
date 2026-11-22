# FINANCIA+

Administrador de finanzas personales con **registro manual**. Proyecto del curso Base de
Datos 1 (UTP, Colombia).

> **Estado: diseño aprobado; migración inicial y pruebas de restricciones escritas y revisadas,
> pero sin ejecutar.** No hay base de datos creada ni código de aplicación todavía. El detalle
> está en [`docs/ESTADO_PROYECTO.md`](docs/ESTADO_PROYECTO.md).

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

## Tecnología prevista

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
├── requirements.txt       Dependencias previstas (sin instalar ni fijar versión)
├── app/                   API FLASK, orientada a objetos (pendiente)
│   ├── entidades/         Clases de datos (una por tabla)
│   ├── rutas/             Reciben peticiones JSON bajo /api/ y responden JSON
│   ├── servicios/         Reglas de negocio y transacciones
│   └── repositorios/      SQL escrito a mano
├── db/                    BASE DE DATOS (pendiente)
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

Cada carpeta de trabajo tiene un `LEEME.md` que explica qué va ahí. Por ahora solo tienen
contenido `db/migraciones/` (la migración `0001`) y `tests/` (pruebas de restricciones).

## Por dónde empezar

1. Lee `docs/ESTADO_PROYECTO.md`.
2. Sigue las tareas de `docs/GUIA_CONTINUIDAD_OPUS.md`, en orden. Las Tareas 3 y 5 ya están
   escritas: falta ejecutarlas y corregir lo que aparezca.

## Instalación

Pendiente. Se escribirá en la Tarea 1 de la guía, con los pasos reales y probados.
