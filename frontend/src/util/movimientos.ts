// Cómo se muestra un movimiento del historial y qué botones se le ofrecen.
//
// Los botones solo siguen lo que la API permite en esta ruta (app/servicios/movimientos.py);
// si alguno se mostrara de más, la API lo rechazaría con su mensaje.
import type { Movimiento, TipoMovimiento } from "../api/tipos";
import { formatearDinero } from "./formato";

export const NOMBRES_TIPO_MOVIMIENTO: Record<TipoMovimiento, string> = {
  INGRESO: "Ingreso",
  EGRESO: "Egreso",
  TRANSFERENCIA: "Transferencia",
  AJUSTE_AUMENTO: "Ajuste (aumento)",
  AJUSTE_DISMINUCION: "Ajuste (disminución)",
};

/** Un cargo es un EGRESO que pertenece a una transferencia (RN-34). */
export function esCargo(m: Movimiento): boolean {
  return m.tipo === "EGRESO" && m.id_transferencia !== null;
}

/** "Egreso" o "Cargo de transferencia", para la etiqueta de la fila. */
export function nombreTipo(m: Movimiento): string {
  return esCargo(m) ? "Cargo de transferencia" : NOMBRES_TIPO_MOVIMIENTO[m.tipo];
}

/** El monto con el efecto sobre el saldo: "+$ 50.000", "−$ 20.000" o "$ 100.000" (transferencia). */
export function montoConSigno(m: Movimiento): string {
  switch (m.tipo) {
    case "INGRESO":
    case "AJUSTE_AUMENTO":
      return `+${formatearDinero(m.monto)}`;
    case "EGRESO":
    case "AJUSTE_DISMINUCION":
      return formatearDinero(`-${m.monto}`);
    case "TRANSFERENCIA":
      return formatearDinero(m.monto);
  }
}

export interface AccionesPermitidas {
  corregir: boolean;          // solo ingresos y egresos propios (no cargos), y vigentes
  anularOReactivar: boolean;  // todo menos la transferencia, que va con sus cargos (RN-38)
}

export function accionesPermitidas(m: Movimiento): AccionesPermitidas {
  const ingresoOEgreso = (m.tipo === "INGRESO" || m.tipo === "EGRESO") && !esCargo(m);
  return {
    corregir: ingresoOEgreso && m.estado === "VIGENTE",
    anularOReactivar: m.tipo !== "TRANSFERENCIA",
  };
}
