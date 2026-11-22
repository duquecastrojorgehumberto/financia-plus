// Pruebas de qué categorías se ofrecen en un formulario: npm test
import { describe, expect, it } from "vitest";

import type { Categoria, RamaCategoria } from "../api/tipos";
import { ramasUtilizables } from "./categorias";

const sub = (id: number, activa: boolean): Categoria =>
  ({ id_categoria: id, id_padre: 1, nombre: `S${id}`, tipo: "EGRESO", activa });
const rama = (id: number, activa: boolean, subcategorias: Categoria[]): RamaCategoria =>
  ({ id_categoria: id, id_padre: null, nombre: `R${id}`, tipo: "EGRESO", activa, subcategorias });

const arbol = [rama(1, true, [sub(11, true), sub(12, false)]), rama(2, false, [sub(21, false)])];
const ids = (rs: RamaCategoria[]) => rs.flatMap((r) => [r.id_categoria, ...r.subcategorias.map((s) => s.id_categoria)]);

describe("ramasUtilizables", () => {
  it("para algo nuevo: solo las activas", () => {
    expect(ids(ramasUtilizables(arbol))).toEqual([1, 11]);
  });

  it("al corregir: también la subcategoría desactivada que ya tiene", () => {
    expect(ids(ramasUtilizables(arbol, 12))).toEqual([1, 11, 12]);
  });

  it("al corregir: la raíz desactivada se muestra si ya era su categoría", () => {
    expect(ids(ramasUtilizables(arbol, 2))).toEqual([1, 11, 2]);
  });

  it("al corregir: una subcategoría desactivada de una raíz desactivada también", () => {
    expect(ids(ramasUtilizables(arbol, 21))).toEqual([1, 11, 2, 21]);
  });
});
