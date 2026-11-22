// Pruebas de los colores de los gráficos: npm test
import { describe, expect, it } from "vitest";

import { COLOR_SIN_COLOR, colorDePosicion, coloresPorId, PALETA, PALETA_PASTEL } from "./colores";

describe("colorDePosicion", () => {
  it("las 8 primeras usan la paleta base, en su orden fijo", () => {
    expect([0, 1, 2, 3, 4, 5, 6, 7].map(colorDePosicion)).toEqual(PALETA);
    expect(colorDePosicion(0)).toBe("#2a78d6");
  });

  it("de la 9.ª a la 16.ª, la versión pastel del mismo orden", () => {
    expect(colorDePosicion(8)).toBe(PALETA_PASTEL[0]);
    expect(colorDePosicion(15)).toBe(PALETA_PASTEL[7]);
  });

  it("de la 17.ª en adelante, gris (nunca se inventa un color)", () => {
    expect(colorDePosicion(16)).toBe(COLOR_SIN_COLOR);
    expect(colorDePosicion(40)).toBe(COLOR_SIN_COLOR);
  });

  it("no hay colores repetidos entre la paleta base y la pastel", () => {
    expect(new Set([...PALETA, ...PALETA_PASTEL, COLOR_SIN_COLOR]).size).toBe(17);
  });
});

describe("coloresPorId: el color sigue a la categoría", () => {
  it("se asigna por orden de creación (id), no por el orden en que llegan", () => {
    const colores = coloresPorId([30, 10, 20]);
    expect(colores.get(10)).toBe(PALETA[0]);
    expect(colores.get(20)).toBe(PALETA[1]);
    expect(colores.get(30)).toBe(PALETA[2]);
  });

  it("una categoría conserva su color aunque cambie su tamaño en otro periodo", () => {
    // El mismo usuario, con las mismas categorías: el resultado no depende de los totales.
    expect(coloresPorId([10, 20, 30]).get(20)).toBe(coloresPorId([30, 20, 10]).get(20));
  });
});
