// Cliente de la API de FINANCIA+: TODAS las peticiones de la interfaz pasan por aquí.
//
// Qué resuelve en un solo lugar:
//   * La ruta: "/cuentas" se convierte en "/api/cuentas" (Vite la reenvía a Flask).
//   * La cookie de sesión: credentials "same-origin" la envía en cada petición.
//   * La protección CSRF (ARQUITECTURA.md, sección 6): toda petición que modifica
//     datos va en JSON y con el encabezado X-Requested-With: financia. Sin eso,
//     Flask la rechaza con 403 o 415.
//   * Los errores: si la API responde un error, se lanza un ErrorApi con el
//     mensaje en español que envió el servidor ({"error": "..."}), listo para
//     mostrarlo al usuario.

/** Un error que respondió la API. "estado" es el código HTTP (400, 401, 404...). */
export class ErrorApi extends Error {
  readonly estado: number;

  constructor(estado: number, mensaje: string) {
    super(mensaje);
    this.name = "ErrorApi";
    this.estado = estado;
  }
}

type Metodo = "GET" | "POST" | "PUT" | "DELETE";

async function pedir<T>(metodo: Metodo, ruta: string, cuerpo?: unknown): Promise<T> {
  const opciones: RequestInit = { method: metodo, credentials: "same-origin" };
  if (metodo !== "GET") {
    opciones.headers = { "Content-Type": "application/json", "X-Requested-With": "financia" };
    opciones.body = JSON.stringify(cuerpo ?? {});
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`/api${ruta}`, opciones);
  } catch {
    throw new ErrorApi(0, "No hay conexión con el servidor. ¿Está encendida la API?");
  }

  const datos: unknown = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    const mensaje =
      typeof datos === "object" && datos !== null && "error" in datos && typeof datos.error === "string"
        ? datos.error
        : "Ocurrió un error inesperado. Intente de nuevo.";
    throw new ErrorApi(respuesta.status, mensaje);
  }
  return datos as T;
}

export const api = {
  get: <T>(ruta: string) => pedir<T>("GET", ruta),
  post: <T>(ruta: string, cuerpo?: unknown) => pedir<T>("POST", ruta, cuerpo),
  put: <T>(ruta: string, cuerpo?: unknown) => pedir<T>("PUT", ruta, cuerpo),
  delete: <T>(ruta: string) => pedir<T>("DELETE", ruta),
};
