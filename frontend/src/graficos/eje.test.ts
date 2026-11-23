// Pruebas de las marcas del eje Y: npm test
import { describe, expect, it } from "vitest";

import { marcasDelEje, pasoRedondo } from "./eje";

describe("pasoRedondo", () => {
  it.each([
    [946_667, 1_000_000],
    [1_000_000, 1_000_000],
    [30_267, 50_000],
    [210_000, 250_000],
    [1_500_001, 2_000_000],
    [0, 1_000],
  ])("%s → %s", (valor, esperado) => {
    expect(pasoRedondo(valor)).toBe(esperado);
  });
});

describe("marcasDelEje", () => {
  it("cubren el máximo con pasos redondos", () => {
    expect(marcasDelEje(2_840_000)).toEqual([0, 1_000_000, 2_000_000, 3_000_000]);
    expect(marcasDelEje(3_000_000)).toEqual([0, 1_000_000, 2_000_000, 3_000_000]);
    expect(marcasDelEje(90_800)).toEqual([0, 50_000, 100_000, 150_000]);
  });

  it("sin movimientos, una escala pequeña (no una división por cero)", () => {
    expect(marcasDelEje(0)).toEqual([0, 1_000, 2_000, 3_000]);
  });
});
