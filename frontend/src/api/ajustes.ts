// Llamadas a los ajustes de saldo (app/rutas/ajustes.py).
//
// Un ajuste es un movimiento AJUSTE_AUMENTO o AJUSTE_DISMINUCION sin categoría; su
// motivo viaja en "descripcion". Se anula y reactiva con las rutas de movimientos.
import { api } from "./cliente";
import { listarMovimientos } from "./movimientos";
import type { Movimiento, ResultadoAjuste } from "./tipos";

/**
 * El usuario da el SALDO REAL que ve en su banco; la API calcula la diferencia con el
 * saldo calculado y, si no es cero, registra el ajuste (RN-50, RN-51). Sin fecha: hoy.
 */
export function ajustarSaldo(idCuenta: number, saldoReal: string, motivo: string, fecha: string): Promise<ResultadoAjuste> {
  return api.post<ResultadoAjuste>(`/cuentas/${idCuenta}/ajustes`, { saldo_real: saldoReal, motivo, fecha });
}

/** Solo la fecha y el motivo: el monto salió de un cálculo y no se corrige. */
export async function corregirAjuste(idAjuste: number, fecha: string, motivo: string): Promise<Movimiento> {
  return (await api.put<{ ajuste: Movimiento }>(`/ajustes/${idAjuste}`, { fecha, motivo })).ajuste;
}

/** Los ajustes de los dos tipos, del más reciente al más antiguo (como el historial). */
export async function listarAjustes(): Promise<Movimiento[]> {
  const [aumentos, disminuciones] = await Promise.all([
    listarMovimientos({ tipo: "AJUSTE_AUMENTO" }),
    listarMovimientos({ tipo: "AJUSTE_DISMINUCION" }),
  ]);
  return [...aumentos, ...disminuciones].sort(
    (a, b) => b.fecha.localeCompare(a.fecha) || b.id_movimiento - a.id_movimiento,
  );
}
