// Llamada al resumen financiero (app/rutas/resumen.py).
import { api } from "./cliente";
import type { RespuestaResumen, TotalMes } from "./tipos";

/** Sin fechas, la API usa el mes actual (P-41). Las fechas van como "AAAA-MM-DD". */
export function consultarResumen(desde?: string, hasta?: string): Promise<RespuestaResumen> {
  const parametros = new URLSearchParams();
  if (desde) parametros.set("desde", desde);
  if (hasta) parametros.set("hasta", hasta);
  const consulta = parametros.toString();
  return api.get<RespuestaResumen>(consulta ? `/resumen?${consulta}` : "/resumen");
}

/** Ingresos y egresos de los últimos `meses` meses (por defecto 6), del más antiguo al más reciente. */
export async function consultarMensual(meses = 6): Promise<TotalMes[]> {
  return (await api.get<{ meses: TotalMes[] }>(`/resumen/mensual?meses=${meses}`)).meses;
}
