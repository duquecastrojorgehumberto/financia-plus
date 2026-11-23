// Marcas "redondas" para el eje Y del gráfico mensual: 0, 1 M, 2 M, 3 M (y no 0, 950 mil,
// 1,9 M, 2,9 M, que es lo que sale al repartir el máximo en partes iguales).
// Es solo para dibujar la escala: trabaja con números porque son las rayas del eje,
// no cifras de dinero que se lean como dato.

const PASOS_REDONDOS = [1, 2, 2.5, 5, 10];

/** El paso redondo más pequeño (1, 2, 2,5 o 5 por una potencia de 10) que sea ≥ valor. */
export function pasoRedondo(valor: number): number {
  if (valor <= 0) return 1000;
  const potencia = 10 ** Math.floor(Math.log10(valor));
  const factor = PASOS_REDONDOS.find((p) => p * potencia >= valor) ?? 10;
  return factor * potencia;
}

/** Cuatro marcas (0 y tres pasos) que cubren el valor más alto. */
export function marcasDelEje(maximo: number, pasos = 3): number[] {
  const paso = pasoRedondo(maximo / pasos);
  return Array.from({ length: pasos + 1 }, (_, i) => i * paso);
}
