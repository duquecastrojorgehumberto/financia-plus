// Pruebas de cómo se muestra un movimiento y qué botones se ofrecen: npm test
import { describe, expect, it } from "vitest";

import type { Movimiento } from "../api/tipos";
import { hoy } from "./formato";
import { accionesPermitidas, esCargo, montoConSigno, nombreTipo } from "./movimientos";

function movimiento(cambios: Partial<Movimiento>): Movimiento {
  return {
    id_movimiento: 1,
    tipo: "EGRESO",
    estado: "VIGENTE",
    fecha: "2026-11-05",
    monto: "20000.00",
    descripcion: null,
    id_cuenta: 1,
    nombre_cuenta: "Nequi",
    id_cuenta_destino: null,
    nombre_cuenta_destino: null,
    id_categoria: 7,
    nombre_categoria: "Mercado",
    id_transferencia: null,
    creado_en: "2026-11-05T10:00:00-05:00",
    actualizado_en: "2026-11-05T10:00:00-05:00",
    ...cambios,
  };
}

describe("montoConSigno", () => {
  it.each([
    ["INGRESO", "+$ 20.000"],
    ["AJUSTE_AUMENTO", "+$ 20.000"],
    ["EGRESO", "−$ 20.000"],
    ["AJUSTE_DISMINUCION", "−$ 20.000"],
    ["TRANSFERENCIA", "$ 20.000"],
  ] as const)("%s → %s", (tipo, esperado) => {
    expect(montoConSigno(movimiento({ tipo }))).toBe(esperado);
  });

  it("no pierde los centavos", () => {
    expect(montoConSigno(movimiento({ monto: "1500.05" }))).toBe("−$ 1.500,05");
  });
});

describe("cargos de transferencia", () => {
  it("un EGRESO con id_transferencia es un cargo", () => {
    const cargo = movimiento({ id_transferencia: 9 });
    expect(esCargo(cargo)).toBe(true);
    expect(nombreTipo(cargo)).toBe("Cargo de transferencia");
  });

  it("un EGRESO normal no es un cargo", () => {
    expect(esCargo(movimiento({}))).toBe(false);
    expect(nombreTipo(movimiento({}))).toBe("Egreso");
  });
});

describe("accionesPermitidas", () => {
  it("ingreso o egreso vigente: corregir y anular", () => {
    expect(accionesPermitidas(movimiento({}))).toEqual({ corregir: true, anularOReactivar: true });
    expect(accionesPermitidas(movimiento({ tipo: "INGRESO" }))).toEqual({ corregir: true, anularOReactivar: true });
  });

  it("anulado: solo reactivar (para corregirlo hay que reactivarlo)", () => {
    expect(accionesPermitidas(movimiento({ estado: "ANULADO" }))).toEqual({ corregir: false, anularOReactivar: true });
  });

  it("cargo: se anula o reactiva, pero no se corrige aquí", () => {
    expect(accionesPermitidas(movimiento({ id_transferencia: 9 }))).toEqual({ corregir: false, anularOReactivar: true });
  });

  it("transferencia: nada aquí (va con sus cargos, RN-38)", () => {
    expect(accionesPermitidas(movimiento({ tipo: "TRANSFERENCIA" }))).toEqual({ corregir: false, anularOReactivar: false });
  });

  it("ajuste: se anula o reactiva, no se corrige aquí", () => {
    expect(accionesPermitidas(movimiento({ tipo: "AJUSTE_AUMENTO", id_categoria: null })))
      .toEqual({ corregir: false, anularOReactivar: true });
  });
});

describe("hoy", () => {
  it("usa la fecha local con dos dígitos", () => {
    expect(hoy(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
    expect(hoy(new Date(2026, 10, 22, 0, 10))).toBe("2026-11-22");
  });
});
