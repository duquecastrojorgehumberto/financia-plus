// Pruebas de la preparación de datos para los gráficos: npm test
import { describe, expect, it } from "vitest";

import type { Bolsillo, TotalCategoria } from "../api/tipos";
import { COLOR_SIN_COLOR } from "./colores";
import { prepararCategorias, prepararMeses, prepararMetas } from "./datos";

const alimentacion: TotalCategoria = {
  id_categoria: 5, nombre: "Alimentación", total: "50000.00", porcentaje: "55.1",
  directo: "20000.00", porcentaje_directo: "22.0",
  subcategorias: [{ id_categoria: 9, nombre: "Mercado", total: "30000.00", porcentaje: "33.0" }],
};

describe("prepararCategorias", () => {
  it("conserva los textos de la API y usa el número solo para el largo", () => {
    const [fila] = prepararCategorias([alimentacion], new Map([[5, "#2a78d6"]]));
    expect(fila).toMatchObject({ nombre: "Alimentación", valor: 50000, total: "50000.00", porcentaje: "55.1", color: "#2a78d6" });
  });

  it("el desglose trae las subcategorías y, si hay, lo directo", () => {
    const [fila] = prepararCategorias([alimentacion], new Map());
    expect(fila.desglose).toEqual([
      { nombre: "Mercado", total: "30000.00", porcentaje: "33.0" },
      { nombre: "Alimentación (directo)", total: "20000.00", porcentaje: "22.0" },
    ]);
  });

  it("sin subcategorías no hay desglose; sin color asignado, gris", () => {
    const [fila] = prepararCategorias([{ ...alimentacion, subcategorias: [] }], new Map());
    expect(fila.desglose).toEqual([]);
    expect(fila.color).toBe(COLOR_SIN_COLOR);
  });
});

describe("prepararMeses", () => {
  it("etiquetas del mes y textos originales para el tooltip", () => {
    const [fila] = prepararMeses([{ mes: "2026-06", ingresos: "3000000.00", egresos: "2350000.50", balance: "649999.50" }]);
    expect(fila).toEqual({
      etiqueta: "jun", etiquetaLarga: "junio 2026", ingresos: 3000000, egresos: 2350000.5, balance: 649999.5,
      textos: { ingresos: "3000000.00", egresos: "2350000.50", balance: "649999.50" },
    });
  });
});

describe("prepararMetas", () => {
  const base: Bolsillo = {
    id_bolsillo: 1, nombre: "Computador", descripcion: null, es_meta: true, monto_objetivo: "1000000.00",
    fecha_objetivo: null, valor_actual: "350000.00", progreso_porcentaje: "35.00", activo: true, creado_en: "",
  };

  it("solo bolsillos activos con meta", () => {
    const filas = prepararMetas([
      base,
      { ...base, id_bolsillo: 2, es_meta: false, monto_objetivo: null, progreso_porcentaje: null },
      { ...base, id_bolsillo: 3, activo: false },
    ], new Map());
    expect(filas.map((f) => f.id)).toEqual([1]);
  });

  it("la barra se detiene en 100, pero el texto muestra el porcentaje real", () => {
    const [meta] = prepararMetas([{ ...base, valor_actual: "1500000.00", progreso_porcentaje: "150.00" }], new Map());
    expect([meta.valor, meta.porcentaje, meta.cumplida]).toEqual([100, "150.00", true]);
  });
});
