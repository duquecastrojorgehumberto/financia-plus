// Pruebas del formato de dinero y fechas: npm test
import { describe, expect, it } from "vitest";

import {
  dineroParaCampo,
  dineroParaEnviar,
  esDineroValido,
  esNegativo,
  formatearDinero,
  formatearEjeDinero,
  formatearFecha,
  formatearFechaHora,
  formatearMes,
  formatearPorcentaje,
  formatearPorcentajeExacto,
} from "./formato";

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

describe("dinero escrito por el usuario", () => {
  it.each([
    ["150000,50", "150000.50"],
    [" 2000 ", "2000"],
    ["150000.50", "150000.50"],
  ])("dineroParaEnviar(%s) → %s", (texto, esperado) => {
    expect(dineroParaEnviar(texto)).toBe(esperado);
  });

  it.each([
    ["130000.00", "130000"],
    ["130000.50", "130000,50"],
    ["0.00", "0"],
  ])("dineroParaCampo(%s) → %s", (valor, esperado) => {
    expect(dineroParaCampo(valor)).toBe(esperado);
  });

  it.each([
    ["150000", true],
    ["150000,5", true],
    ["150000.50", true],
    ["0", true],
    ["1.000.000", false],
    ["10,505", false],
    ["-5", false],
    ["abc", false],
    ["", false],
  ])("esDineroValido(%s) → %s", (texto, esperado) => {
    expect(esDineroValido(texto)).toBe(esperado);
  });

  it.each([
    ["-50000", true],
    ["-50000,5", true],
    ["50000", true],
    ["--5", false],
    ["5-", false],
  ])("esDineroValido(%s, permitirNegativo) → %s", (texto, esperado) => {
    expect(esDineroValido(texto, true)).toBe(esperado);
  });
});

describe("formatearPorcentaje", () => {
  it.each([
    ["35.00", "35 %"],
    ["33.33", "33,33 %"],
    ["120.50", "120,5 %"],
    ["0.00", "0 %"],
  ])("%s → %s", (valor, esperado) => {
    expect(formatearPorcentaje(valor)).toBe(esperado);
  });
});

describe("formatearFechaHora", () => {
  it("muestra la hora del computador con dos dígitos", () => {
    const local = new Date(2026, 10, 5, 9, 7);   // 5 nov 2026, 09:07 en la zona del computador
    expect(formatearFechaHora(local.toISOString())).toBe("5 nov 2026, 09:07");
  });
});

describe("formatearMes", () => {
  it.each([
    ["2026-06", false, "jun"],
    ["2026-06", true, "junio 2026"],
    ["2027-01", true, "enero 2027"],
  ])("%s (largo: %s) → %s", (mes, largo, esperado) => {
    expect(formatearMes(mes, largo)).toBe(esperado);
  });
});

describe("formatearEjeDinero (marcas del eje)", () => {
  it.each([
    [0, "$ 0"],
    [800, "$ 800"],
    [800000, "$ 800 mil"],
    [1000000, "$ 1 M"],
    [2500000, "$ 2,5 M"],
    [-500000, "−$ 500 mil"],
  ])("%s → %s", (valor, esperado) => {
    expect(formatearEjeDinero(valor)).toBe(esperado);
  });
});

describe("formatearPorcentajeExacto", () => {
  it.each([
    ["2.0", "2,0 %"],
    ["54.1", "54,1 %"],
    ["100.0", "100,0 %"],
  ])("%s → %s", (valor, esperado) => {
    expect(formatearPorcentajeExacto(valor)).toBe(esperado);
  });
});
