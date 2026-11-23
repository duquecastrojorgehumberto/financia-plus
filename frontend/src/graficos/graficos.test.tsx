// @vitest-environment jsdom
// Pruebas de los componentes de gráficos: npm test
//
// Se dibujan en jsdom (un navegador simulado). jsdom no mide anchos, así que aquí se
// simula ResizeObserver con un ancho fijo de 800 px. Lo que se comprueba es lo que el
// usuario LEE: nombres, cifras con formato colombiano, porcentajes de la API, orden y textos.
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import type { Bolsillo, TotalCategoria, TotalMes } from "../api/tipos";
import { COLOR_EGRESOS, COLOR_INGRESOS, coloresPorId, PALETA } from "./colores";
import { prepararCategorias, prepararMeses, prepararMetas } from "./datos";
import { GraficoCategorias } from "./GraficoCategorias";
import { GraficoDona } from "./GraficoDona";
import { GraficoMensual } from "./GraficoMensual";
import { ProgresoMetas } from "./ProgresoMetas";

beforeAll(() => {
  class ResizeObserverFalso {
    constructor(private avisar: (entradas: { contentRect: { width: number } }[]) => void) {}
    observe() {
      this.avisar([{ contentRect: { width: 800 } }]);
    }
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverFalso as unknown as typeof ResizeObserver;
});

afterEach(cleanup);

const CATEGORIAS: TotalCategoria[] = [
  { id_categoria: 2, nombre: "Vivienda", total: "7082000.00", porcentaje: "54.1", directo: "0.00",
    porcentaje_directo: "0.0", subcategorias: [] },
  { id_categoria: 1, nombre: "Alimentación", total: "2805000.00", porcentaje: "21.4", directo: "20000.00",
    porcentaje_directo: "0.2", subcategorias: [{ id_categoria: 9, nombre: "Mercado", total: "2785000.00", porcentaje: "21.3" }] },
  { id_categoria: 3, nombre: "Salud", total: "260000.00", porcentaje: "2.0", directo: "260000.00",
    porcentaje_directo: "2.0", subcategorias: [] },
];
const colores = coloresPorId([1, 2, 3]);
const filasCategorias = prepararCategorias(CATEGORIAS, colores);

/** Los textos de un SVG, en orden, como los lee el usuario. */
const textosSvg = (contenedor: HTMLElement) => [...contenedor.querySelectorAll("svg text")].map((t) => t.textContent);

describe("GraficoCategorias", () => {
  it("cada barra con su nombre y sus cifras encima, en el orden de la API (de mayor a menor)", async () => {
    const { container } = render(<GraficoCategorias filas={filasCategorias} />);
    await waitFor(() => expect(textosSvg(container)).toContain("Vivienda"));
    expect(textosSvg(container)).toEqual([
      "Vivienda", "$ 7.082.000 · 54,1 %",
      "Alimentación", "$ 2.805.000 · 21,4 %",
      "Salud", "$ 260.000 · 2,0 %",   // un decimal siempre: la columna queda pareja
    ]);
  });

  it("el color sigue a la categoría (orden de creación), no a su posición", async () => {
    const { container } = render(<GraficoCategorias filas={filasCategorias} />);
    await waitFor(() => expect(container.querySelectorAll(".recharts-bar-rectangle path").length).toBe(3));
    const rellenos = [...container.querySelectorAll(".recharts-bar-rectangle path")].map((p) => p.getAttribute("fill"));
    // Vivienda va primero en el gráfico, pero fue la 2.ª en crearse: segundo color.
    expect(rellenos).toEqual([PALETA[1], PALETA[0], PALETA[2]]);
  });

  it("sin categorías no dibuja nada", () => {
    const { container } = render(<GraficoCategorias filas={[]} />);
    expect(container.querySelector("svg")).toBeNull();
  });
});

const MESES: TotalMes[] = [
  { mes: "2026-10", ingresos: "2400000.00", egresos: "2840000.00", balance: "-440000.00" },
  { mes: "2026-11", ingresos: "50000.00", egresos: "90800.00", balance: "-40800.00" },
];

describe("GraficoMensual", () => {
  it("leyenda en orden fijo (Ingresos, Egresos) con los dos primeros colores", async () => {
    const { container } = render(<GraficoMensual filas={prepararMeses(MESES)} />);
    await waitFor(() => expect(container.querySelector(".leyenda-series")).not.toBeNull());
    const items = [...container.querySelectorAll(".leyenda-series li")];
    expect(items.map((li) => li.textContent)).toEqual(["Ingresos", "Egresos"]);
    expect(items.map((li) => (li.querySelector(".punto") as HTMLElement).style.background))
      .toEqual([COLOR_INGRESOS, COLOR_EGRESOS].map((c) => hexARgb(c)));
  });

  it("un mes por grupo, con su etiqueta, y un solo eje Y con montos abreviados", async () => {
    const { container } = render(<GraficoMensual filas={prepararMeses(MESES)} />);
    await waitFor(() => expect(textosSvg(container)).toContain("oct"));
    expect(textosSvg(container)).toEqual(expect.arrayContaining(["oct", "nov", "$ 0", "$ 3 M"]));
    expect(container.querySelectorAll(".recharts-yAxis").length).toBe(1);
  });
});

describe("GraficoDona", () => {
  it("el total en el centro y una leyenda con nombre, porcentaje y monto", () => {
    render(<GraficoDona filas={filasCategorias} total="10147000.00" />);
    expect(screen.getByText("$ 10.147.000")).toBeTruthy();
    const filas = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(filas).toEqual(["Vivienda54,1 %$ 7.082.000", "Alimentación21,4 %$ 2.805.000", "Salud2,0 %$ 260.000"]);
  });
});

const BOLSILLO: Bolsillo = {
  id_bolsillo: 1, nombre: "Bicicleta", descripcion: null, es_meta: true, monto_objetivo: "400000.00",
  fecha_objetivo: "2027-03-31", valor_actual: "120000.00", progreso_porcentaje: "30.00", activo: true, creado_en: "",
};

describe("ProgresoMetas", () => {
  it("una tarjeta por meta con porcentaje, barra y montos", () => {
    render(<ProgresoMetas filas={prepararMetas([BOLSILLO], coloresPorId([1]))} />);
    const cabecera = screen.getByRole("listitem").querySelector(".meta-cabecera") as HTMLElement;
    const tarjeta = screen.getByRole("listitem");
    expect(within(cabecera).getByText("Bicicleta")).toBeTruthy();
    expect(within(cabecera).getByText("30 %")).toBeTruthy();
    expect(within(tarjeta).getByText("$ 120.000 de $ 400.000")).toBeTruthy();
    expect(within(tarjeta).getByRole("progressbar").getAttribute("aria-valuenow")).toBe("30");
  });

  it("una meta superada: barra llena, pero el texto con el porcentaje real y la marca de cumplida", () => {
    const superada = { ...BOLSILLO, valor_actual: "600000.00", progreso_porcentaje: "150.00" };
    render(<ProgresoMetas filas={prepararMetas([superada], new Map())} />);
    expect(screen.getByText("150 % ✓")).toBeTruthy();
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("100");
  });

  it("el detalle (para el mouse o el toque) trae la meta y la fecha", () => {
    render(<ProgresoMetas filas={prepararMetas([BOLSILLO], new Map())} />);
    const detalle = screen.getByRole("tooltip");
    expect(within(detalle).getByText("$ 400.000")).toBeTruthy();
    expect(within(detalle).getByText("31 mar 2027")).toBeTruthy();
  });

  it("sin metas, un mensaje", () => {
    render(<ProgresoMetas filas={[]} />);
    expect(screen.getByText("No hay bolsillos con meta.")).toBeTruthy();
  });
});

/** "#2a78d6" → "rgb(42, 120, 214)": así devuelve jsdom un color de style. */
function hexARgb(hex: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return `rgb(${r}, ${g}, ${b})`;
}
