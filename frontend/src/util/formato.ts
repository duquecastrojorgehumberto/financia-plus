// Formato para mostrar dinero y fechas en pesos colombianos.
//
// formatearDinero trabaja con el TEXTO que envía la API ("1032700.50") y nunca
// lo convierte a número: Number("0.1") + Number("0.2") da 0.30000000000000004.
// Solo agrega los separadores de miles: así un valor nunca cambia al mostrarlo.

/** "1032700.50" → "$ 1.032.700,50"   "-50000.00" → "−$ 50.000"   (sin ",00") */
export function formatearDinero(valor: string): string {
  const negativo = valor.startsWith("-");
  const [entero, decimales = ""] = valor.replace("-", "").split(".");
  const conMiles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const centavos = decimales.padEnd(2, "0").slice(0, 2);
  const texto = centavos === "00" ? conMiles : `${conMiles},${centavos}`;
  return `${negativo ? "−" : ""}$ ${texto}`;
}

/** true si el texto de dinero es menor que cero, sin convertirlo a número. */
export function esNegativo(valor: string): boolean {
  return valor.startsWith("-") && /[1-9]/.test(valor);
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** "2026-11-05" → "5 nov 2026". Se lee del texto, sin Date, para no correr el día por la zona horaria. */
export function formatearFecha(fecha: string): string {
  const [anio, mes, dia] = fecha.split("-");
  return `${Number(dia)} ${MESES[Number(mes) - 1]} ${anio}`;
}
