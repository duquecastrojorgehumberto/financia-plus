// Llamadas a las transferencias (app/rutas/transferencias.py). Una función por ruta de la API.
//
// Un cargo es un EGRESO normal: se anula y reactiva con las rutas de movimientos
// (anularMovimiento / reactivarMovimiento en movimientos.ts).
import { api } from "./cliente";
import { listarMovimientos } from "./movimientos";
import type { DatosCargo, DatosTransferencia, Movimiento, Transferencia } from "./tipos";

/** Las transferencias salen del historial, filtradas por tipo. */
export function listarTransferencias(): Promise<Movimiento[]> {
  return listarMovimientos({ tipo: "TRANSFERENCIA" });
}

export async function obtenerTransferencia(id: number): Promise<Transferencia> {
  return (await api.get<{ transferencia: Transferencia }>(`/transferencias/${id}`)).transferencia;
}

/** Transferencia y cargos en UNA transacción: se guardan todos o ninguno (RN-37, CA-03). */
export async function registrarTransferencia(datos: DatosTransferencia, cargos: DatosCargo[]): Promise<Transferencia> {
  return (await api.post<{ transferencia: Transferencia }>("/transferencias", { ...datos, cargos })).transferencia;
}

/** Corrige la transferencia, no sus cargos (cada cargo se corrige aparte). */
export async function corregirTransferencia(id: number, datos: DatosTransferencia): Promise<Transferencia> {
  return (await api.put<{ transferencia: Transferencia }>(`/transferencias/${id}`, datos)).transferencia;
}

/** Anula también sus cargos vigentes, en la misma transacción (RN-38, CA-04). */
export async function anularTransferencia(id: number): Promise<Transferencia> {
  return (await api.post<{ transferencia: Transferencia }>(`/transferencias/${id}/anular`)).transferencia;
}

/** Reactiva solo la transferencia: los cargos se reactivan uno por uno. */
export async function reactivarTransferencia(id: number): Promise<Transferencia> {
  return (await api.post<{ transferencia: Transferencia }>(`/transferencias/${id}/reactivar`)).transferencia;
}

export async function agregarCargo(id: number, cargo: DatosCargo): Promise<Transferencia> {
  return (await api.post<{ transferencia: Transferencia }>(`/transferencias/${id}/cargos`, cargo)).transferencia;
}

export async function corregirCargo(id: number, idCargo: number, cargo: DatosCargo): Promise<Transferencia> {
  return (await api.put<{ transferencia: Transferencia }>(`/transferencias/${id}/cargos/${idCargo}`, cargo))
    .transferencia;
}
