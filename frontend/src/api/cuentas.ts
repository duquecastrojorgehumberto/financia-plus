// Llamadas a las cuentas (app/rutas/cuentas.py). Una función por ruta de la API.
import { api } from "./cliente";
import type { Cuenta, DatosCuenta } from "./tipos";

/** Sin archivadas, la API devuelve solo las cuentas activas. */
export async function listarCuentas(incluirArchivadas = false): Promise<Cuenta[]> {
  const ruta = incluirArchivadas ? "/cuentas?archivadas=1" : "/cuentas";
  return (await api.get<{ cuentas: Cuenta[] }>(ruta)).cuentas;
}

export async function crearCuenta(datos: DatosCuenta): Promise<Cuenta> {
  return (await api.post<{ cuenta: Cuenta }>("/cuentas", datos)).cuenta;
}

export async function editarCuenta(idCuenta: number, datos: DatosCuenta): Promise<Cuenta> {
  return (await api.put<{ cuenta: Cuenta }>(`/cuentas/${idCuenta}`, datos)).cuenta;
}

/** La API solo la archiva si el saldo es 0 (RN-12, CA-15); si no, responde el motivo. */
export async function archivarCuenta(idCuenta: number): Promise<Cuenta> {
  return (await api.post<{ cuenta: Cuenta }>(`/cuentas/${idCuenta}/archivar`)).cuenta;
}

export async function reactivarCuenta(idCuenta: number): Promise<Cuenta> {
  return (await api.post<{ cuenta: Cuenta }>(`/cuentas/${idCuenta}/reactivar`)).cuenta;
}
