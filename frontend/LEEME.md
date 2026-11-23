# frontend/ — Interfaz React

**Estado:** completa (pasos 1 a 7) — base del proyecto, conexión con la API, registro, inicio y
cierre de sesión, y las pantallas de **resumen**, **movimientos**, **transferencias**, **ajustes**,
**bolsillos**, **cuentas** y **categorías**, con gráficos en el resumen y en los bolsillos. Las rutas
de la API que usa cada una están en `README.md`.

React + Vite + TypeScript (decisión D-21), con React Router para las pantallas y CSS propio,
sin librerías de componentes. Los gráficos usan Recharts. Consume la API JSON de Flask bajo `/api/`.

## Cómo arrancarla (Windows, PowerShell)

Se necesitan **dos ventanas** de PowerShell, porque son dos servidores.

Ventana 1 — la API (como siempre):

```powershell
cd C:\Users\thedr\proyectos\financia-plus
```

```powershell
.venv\Scripts\flask --app app run --debug
```

Ventana 2 — la interfaz. La primera vez, instalar las dependencias:

```powershell
cd C:\Users\thedr\proyectos\financia-plus\frontend
```

```powershell
npm install
```

Y cada vez que se quiera usar:

```powershell
npm run dev
```

Abrir http://localhost:5173 en el navegador. Con los datos de demostración cargados, se puede
entrar como `ana@demo.example` o `carla@demo.example` (contraseña `demo-financia-2026`).

Otros comandos (en `frontend/`):

| Comando | Qué hace |
| --- | --- |
| `npm test` | Pruebas de la interfaz (Vitest). Los gráficos se prueban en `jsdom`, un navegador simulado. |
| `npm run verificar-tipos` | Revisa los tipos de TypeScript sin compilar. |
| `npm run build` | Revisa los tipos y genera la versión final en `dist/`. |

## Cómo se conecta con la API

El navegador le pide todo a Vite (`localhost:5173`); Vite **reenvía** a Flask (`127.0.0.1:5000`)
lo que empieza por `/api` (proxy en `vite.config.ts`). Así interfaz y API comparten origen: la
cookie de sesión funciona sin CORS y `SameSite=Lax` sigue protegiendo (ARQUITECTURA.md, sección 6).

Para usar otra API (por ejemplo, una conectada a la base de pruebas en el puerto 5001), se
define `FINANCIA_API` antes de arrancar:

```powershell
$env:FINANCIA_API = "http://127.0.0.1:5001"; npm run dev
```

## Archivos

| Archivo | Qué hace |
| --- | --- |
| `vite.config.ts` | Servidor de desarrollo y el proxy de `/api` hacia Flask. |
| `src/main.tsx` | Punto de entrada: monta la aplicación en `index.html`. |
| `src/App.tsx` | Qué pantalla muestra cada dirección (React Router). |
| `src/api/cliente.ts` | **Todas** las peticiones pasan por aquí: JSON, cookie, encabezado CSRF `X-Requested-With: financia` y errores (`ErrorApi` con el mensaje en español de la API). |
| `src/api/tipos.ts` | Tipos de TypeScript con la forma exacta del JSON de la API. |
| `src/api/sesion.ts`, `resumen.ts`, `cuentas.ts`, `categorias.ts`, `movimientos.ts`, `transferencias.ts`, `ajustes.ts`, `bolsillos.ts` | Una función por llamada a la API. |
| `src/sesion/ContextoSesion.tsx` | Quién tiene la sesión (contexto de React). Se lo pregunta al servidor al abrir la página; no guarda nada en el navegador. |
| `src/componentes/RutaProtegida.tsx` | Sin sesión, lleva a "Iniciar sesión". La protección real está en la API (401). |
| `src/componentes/Plantilla.tsx` | Encabezado, menú y "Cerrar sesión" de las pantallas con sesión. |
| `src/paginas/IniciarSesion.tsx`, `Registro.tsx` | Formularios de sesión; el botón se deshabilita mientras espera (evita el doble envío). |
| `src/componentes/CampoDinero.tsx` | Campo para escribir dinero (texto, no número). Debajo muestra cómo quedó el monto. |
| `src/componentes/SelectorCategoria.tsx` | Lista de categorías con sus subcategorías ("Alimentación › Mercado"). |
| `src/paginas/Movimientos.tsx` | Historial con filtros; registrar, corregir, anular y reactivar ingresos y egresos. Muestra también transferencias, cargos, ajustes y anulados. |
| `src/paginas/Transferencias.tsx` | Transferencias con sus cargos: registrar (con cero o más cargos, todo o nada), corregir, anular (con sus cargos) y reactivar; cada cargo se agrega, corrige, anula y reactiva aparte. |
| `src/paginas/Ajustes.tsx` | Ajustar el saldo de una cuenta con el saldo real (la API calcula la diferencia); corregir fecha y motivo, anular y reactivar ajustes. |
| `src/paginas/Bolsillos.tsx` | Bolsillos y metas: valor actual, barra de progreso, historial; crear, editar, cambiar valor, archivar y reactivar. |
| `src/paginas/Cuentas.tsx` | Cuentas con su saldo: crear, editar, archivar y reactivar. Muestra el mensaje de la API cuando una regla lo impide (archivar con saldo, cambiar el saldo inicial con movimientos, nombre repetido). |
| `src/paginas/Categorias.tsx` | Árbol de categorías por tipo (pestañas Egresos / Ingresos): crear raíces y subcategorías, renombrar, desactivar (con confirmación si arrastra subcategorías) y reactivar. |
| `src/paginas/Resumen.tsx` | Indicadores con aviso si el disponible es negativo, periodo, ajustes aparte y totales por categoría. No calcula nada: muestra lo que calcula la API. |
| `src/util/formato.ts` | Dinero y fechas para mostrar, y el dinero que escribe el usuario ("150000,50" → "150000.50"). Trabaja con texto, sin convertirlo a número. |
| `src/util/categorias.ts` | Qué categorías ofrecer en un formulario: las activas y, al corregir, la que ya tiene. |
| `src/util/movimientos.ts` | Cómo se muestra un movimiento (monto con signo, "Cargo de transferencia") y qué botones se le ofrecen. |
| `src/graficos/colores.ts` | Paleta fija de 8 colores y su versión pastel. El color sigue a la categoría (o al bolsillo) por orden de creación: 1.ª a 8.ª, paleta; 9.ª a 16.ª, pastel; después, gris. |
| `src/graficos/datos.ts` | Prepara los datos de la API para los gráficos. Único lugar donde el dinero pasa a número, y solo para el largo de las barras. |
| `src/graficos/GraficoMensual.tsx` | Ingresos vs egresos de los últimos 6 meses (Resumen). |
| `src/graficos/GraficoCategorias.tsx` | Egresos por categoría en barras, con nombre y cifras encima (Resumen). |
| `src/graficos/GraficoDona.tsx` | Distribución de los egresos en un anillo con el total en el centro (Resumen). |
| `src/graficos/ProgresoMetas.tsx` | Progreso de los bolsillos con meta, en tarjetas (Bolsillos). |
| `src/graficos/Tooltips.tsx`, `eje.ts`, `useAncho.ts`, `animacion.ts` | Tooltips, marcas redondas del eje, ancho disponible y "reducir el movimiento". |
| `src/estilos.css` | Estilos; colores y medidas en variables al inicio. |

## Reglas de la interfaz

- **No repite reglas de negocio**: las decide la API y la interfaz muestra su mensaje. Solo ayuda
  con lo evidente (campos obligatorios, mínimo 8 caracteres en la contraseña).
- **El dinero nunca se convierte a número** para mostrarlo ni enviarlo: viaja como texto. El
  usuario lo escribe sin puntos de miles y con coma para los centavos ("150000,50").
- **El `id_usuario` nunca se envía**: la API lo toma de la sesión (RN-05).
