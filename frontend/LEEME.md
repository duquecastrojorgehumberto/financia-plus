# frontend/ — Interfaz React

**Estado:** paso 1 hecho — base del proyecto, conexión con la API, registro, inicio y cierre de
sesión, y la pantalla de **resumen**. Faltan las pantallas de cuentas, categorías, movimientos,
transferencias, ajustes y bolsillos (la API ya las ofrece: ver la tabla de rutas en `README.md`).

React + Vite + TypeScript (decisión D-21), con React Router para las pantallas y CSS propio,
sin librerías de componentes. Consume la API JSON de Flask bajo `/api/`.

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
| `npm test` | Pruebas de la interfaz (Vitest). |
| `npm run verificar-tipos` | Revisa los tipos de TypeScript sin compilar. |
| `npm run build` | Revisa los tipos y genera la versión final en `dist/`. |

## Cómo se conecta con la API

El navegador le pide todo a Vite (`localhost:5173`); Vite **reenvía** a Flask (`127.0.0.1:5000`)
lo que empieza por `/api` (proxy en `vite.config.ts`). Así interfaz y API comparten origen: la
cookie de sesión funciona sin CORS y `SameSite=Lax` sigue protegiendo (ARQUITECTURA.md, sección 6).

## Archivos

| Archivo | Qué hace |
| --- | --- |
| `vite.config.ts` | Servidor de desarrollo y el proxy de `/api` hacia Flask. |
| `src/main.tsx` | Punto de entrada: monta la aplicación en `index.html`. |
| `src/App.tsx` | Qué pantalla muestra cada dirección (React Router). |
| `src/api/cliente.ts` | **Todas** las peticiones pasan por aquí: JSON, cookie, encabezado CSRF `X-Requested-With: financia` y errores (`ErrorApi` con el mensaje en español de la API). |
| `src/api/tipos.ts` | Tipos de TypeScript con la forma exacta del JSON de la API. |
| `src/api/sesion.ts`, `src/api/resumen.ts` | Una función por llamada a la API. |
| `src/sesion/ContextoSesion.tsx` | Quién tiene la sesión (contexto de React). Se lo pregunta al servidor al abrir la página; no guarda nada en el navegador. |
| `src/componentes/RutaProtegida.tsx` | Sin sesión, lleva a "Iniciar sesión". La protección real está en la API (401). |
| `src/componentes/Plantilla.tsx` | Encabezado, menú y "Cerrar sesión" de las pantallas con sesión. |
| `src/paginas/IniciarSesion.tsx`, `Registro.tsx` | Formularios de sesión; el botón se deshabilita mientras espera (evita el doble envío). |
| `src/paginas/Resumen.tsx` | Indicadores con aviso si el disponible es negativo, periodo, ajustes aparte y totales por categoría. No calcula nada: muestra lo que calcula la API. |
| `src/util/formato.ts` | Dinero y fechas para mostrar. Trabaja con el texto de la API, sin convertirlo a número. |
| `src/estilos.css` | Estilos; colores y medidas en variables al inicio. |

## Reglas de la interfaz

- **No repite reglas de negocio**: las decide la API y la interfaz muestra su mensaje. Solo ayuda
  con lo evidente (campos obligatorios, mínimo 8 caracteres en la contraseña).
- **El dinero nunca se convierte a número** para mostrarlo ni enviarlo: viaja como texto.
- **El `id_usuario` nunca se envía**: la API lo toma de la sesión (RN-05).
