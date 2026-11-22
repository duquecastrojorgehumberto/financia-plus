// Colores de los gráficos. Lista FIJA: nunca se generan colores nuevos.
//
// PALETA: los 8 colores base, en este orden (validados para daltonismo).
// PALETA_PASTEL: los mismos 8, mezclados al 55 % con blanco (calculados una vez y
// escritos aquí). Los usan las categorías 9.ª a 16.ª, que suelen ser las menos
// usadas (decisión del estudiante: "colores pasteles para los egresos menos significativos").
//
// El color SIGUE A LA CATEGORÍA, no a su posición en el gráfico: se asigna por orden
// de creación (id_categoria), así una categoría tiene el mismo color en todos los
// gráficos y en todos los periodos. Como las categorías no se borran (solo se
// desactivan, RN-25), ese orden no cambia nunca.

export const PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];

export const PALETA_PASTEL = ["#9fc2ed", "#f6bba4", "#98dbc3", "#f7d58c", "#f5c4d6", "#8cc78c", "#b8b0ed", "#f2adad"];

/** Gris para lo que no alcanza color propio (de la 17.ª categoría en adelante). */
export const COLOR_SIN_COLOR = "#9aa3ad";

/** Ingresos y egresos del gráfico mensual: los dos primeros colores (no verde y rojo). */
export const COLOR_INGRESOS = PALETA[0];
export const COLOR_EGRESOS = PALETA[1];
export const COLOR_BALANCE = PALETA[6];

// Los mismos valores de estilos.css (--color-texto, --color-suave...). Se repiten aquí
// porque los gráficos se dibujan en SVG y necesitan el color como valor.
export const COLOR_TEXTO = "#1d2733";
export const COLOR_SUAVE = "#5b6878";
export const COLOR_CUADRICULA = "#e6eaf0";
export const COLOR_PISTA = "#eef1f5";

/** El color de la posición n (0, 1, 2...) en orden de creación. */
export function colorDePosicion(posicion: number): string {
  if (posicion < PALETA.length) return PALETA[posicion];
  if (posicion < PALETA.length * 2) return PALETA_PASTEL[posicion - PALETA.length];
  return COLOR_SIN_COLOR;
}

/**
 * id → color, ordenando por id (orden de creación). Recibe TODAS las categorías raíz de
 * un tipo, también las desactivadas, para que el orden no dependa de lo que se ve hoy.
 */
export function coloresPorId(ids: number[]): Map<number, string> {
  const ordenados = [...ids].sort((a, b) => a - b);
  return new Map(ordenados.map((id, posicion) => [id, colorDePosicion(posicion)]));
}
