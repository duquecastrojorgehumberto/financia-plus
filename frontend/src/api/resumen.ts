// Llamada al resumen financiero (app/rutas/resumen.py).
import { api } from "./cliente";
import type { RespuestaResumen } from "./tipos";

/** Sin fechas, la API usa el mes actual (P-41). Las fechas van como "AAAA-MM-DD". */
export function consultarResumen(desde?: string, hasta?: string): Promise<RespuestaResumen> {
  const parametros = new URLSearchParams();
  if (desde) parametros.set("desde", desde);
  if (hasta) parametros.set("hasta", hasta);
  const consulta = parametros.toString();
  return api.get<RespuestaResumen>(consulta ? `/resumen?${consulta}` : "/resumen");
}
