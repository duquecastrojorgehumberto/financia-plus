// Llamadas a los movimientos (app/rutas/movimientos.py). Una función por ruta de la API.
import { api } from "./cliente";
import type { DatosMovimiento, FiltroHistorial, Movimiento } from "./tipos";

/** El historial, del más reciente al más antiguo. Solo se envían los filtros que tienen valor. */
export async function listarMovimientos(filtro: FiltroHistorial = {}): Promise<Movimiento[]> {
  const parametros = new URLSearchParams();
  for (const [campo, valor] of Object.entries(filtro)) {
    if (valor !== undefined && valor !== "") parametros.set(campo, String(valor));
  }
  const consulta = parametros.toString();
  return (await api.get<{ movimientos: Movimiento[] }>(consulta ? `/movimientos?${consulta}` : "/movimientos"))
    .movimientos;
}

export async function registrarMovimiento(tipo: "INGRESO" | "EGRESO", datos: DatosMovimiento): Promise<Movimiento> {
  return (await api.post<{ movimiento: Movimiento }>("/movimientos", { tipo, ...datos })).movimiento;
}

/** El tipo no se envía: no se puede cambiar (RN-72). */
export async function corregirMovimiento(idMovimiento: number, datos: DatosMovimiento): Promise<Movimiento> {
  return (await api.put<{ movimiento: Movimiento }>(`/movimientos/${idMovimiento}`, datos)).movimiento;
}

/** No se borra: cambia a ANULADO y sigue en el historial (RN-70, CA-13). */
export async function anularMovimiento(idMovimiento: number): Promise<Movimiento> {
  return (await api.post<{ movimiento: Movimiento }>(`/movimientos/${idMovimiento}/anular`)).movimiento;
}

export async function reactivarMovimiento(idMovimiento: number): Promise<Movimiento> {
  return (await api.post<{ movimiento: Movimiento }>(`/movimientos/${idMovimiento}/reactivar`)).movimiento;
}
