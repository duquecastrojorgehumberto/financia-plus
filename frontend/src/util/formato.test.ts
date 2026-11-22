// Pruebas del formato de dinero y fechas: npm test
import { describe, expect, it } from "vitest";

import { esNegativo, formatearDinero, formatearFecha } from "./formato";

describe("formatearDinero", () => {
  it.each([
    ["0.00", "$ 0"],
    ["800.00", "$ 800"],
    ["130000.00", "$ 130.000"],
    ["1032700.50", "$ 1.032.700,50"],
    ["999999999999.99", "$ 999.999.999.999,99"],
    ["-50000.00", "−$ 50.000"],
    ["12.5", "$ 12,50"],
    ["7", "$ 7"],
  ])("%s → %s", (valor, esperado) => {
    expect(formatearDinero(valor)).toBe(esperado);
  });

  it("no pierde centavos en valores que un float redondearía", () => {
    expect(formatearDinero("9007199254740993.01")).toBe("$ 9.007.199.254.740.993,01");
  });
});

describe("esNegativo", () => {
  it.each([
    ["-50000.00", true],
    ["50000.00", false],
    ["0.00", false],
    ["-0.00", false],
  ])("%s → %s", (valor, esperado) => {
    expect(esNegativo(valor)).toBe(esperado);
  });
});

describe("formatearFecha", () => {
  it("lee la fecha del texto, sin correr el día por la zona horaria", () => {
    expect(formatearFecha("2026-11-01")).toBe("1 nov 2026");
    expect(formatearFecha("2027-06-30")).toBe("30 jun 2027");
  });
});
