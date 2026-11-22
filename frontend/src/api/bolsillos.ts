// Llamadas a los bolsillos y metas (app/rutas/bolsillos.py). Una función por ruta de la API.
import { api } from "./cliente";
import type { Bolsillo, DatosBolsillo, ValorBolsillo } from "./tipos";

export async function listarBolsillos(incluirArchivados = false): Promise<Bolsillo[]> {
  const ruta = incluirArchivados ? "/bolsillos?archivados=1" : "/bolsillos";
  return (await api.get<{ bolsillos: Bolsillo[] }>(ruta)).bolsillos;
}

/** El historial de valores, del más reciente al más antiguo. */
export async function historialBolsillo(id: number): Promise<ValorBolsillo[]> {
  return (await api.get<{ bolsillo: Bolsillo; historial: ValorBolsillo[] }>(`/bolsillos/${id}`)).historial;
}

/** El bolsillo y su primer valor se guardan juntos (RN-45). */
export async function crearBolsillo(datos: DatosBolsillo, valor: string): Promise<Bolsillo> {
  return (await api.post<{ bolsillo: Bolsillo }>("/bolsillos", { ...datos, valor })).bolsillo;
}

/** Nombre, descripción y meta. El valor NO va aquí: se cambia con cambiarValor (RN-44). */
export async function editarBolsillo(id: number, datos: DatosBolsillo): Promise<Bolsillo> {
  return (await api.put<{ bolsillo: Bolsillo }>(`/bolsillos/${id}`, datos)).bolsillo;
}

/** registrado es false si el valor era igual al actual: no se agrega al historial (RN-46). */
export function cambiarValor(id: number, valor: string): Promise<{ bolsillo: Bolsillo; registrado: boolean }> {
  return api.post<{ bolsillo: Bolsillo; registrado: boolean }>(`/bolsillos/${id}/valor`, { valor });
}

export async function archivarBolsillo(id: number): Promise<Bolsillo> {
  return (await api.post<{ bolsillo: Bolsillo }>(`/bolsillos/${id}/archivar`)).bolsillo;
}

export async function reactivarBolsillo(id: number): Promise<Bolsillo> {
  return (await api.post<{ bolsillo: Bolsillo }>(`/bolsillos/${id}/reactivar`)).bolsillo;
}
