// Preparar los datos de la API para los gráficos.
//
// La librería de gráficos necesita NÚMEROS para saber qué tan larga dibujar cada barra.
// Este es el ÚNICO lugar donde el dinero (que llega como texto) se convierte a número,
// y solo para dibujar: todas las cifras que se leen en pantalla (etiquetas, tooltips)
// se muestran desde el texto original con formatearDinero, así no se pierde un centavo.
// Aquí no se calcula ningún total ni porcentaje: vienen de la API.
import type { Bolsillo, TotalCategoria, TotalMes } from "../api/tipos";
import { formatearMes } from "../util/formato";
import { COLOR_SIN_COLOR } from "./colores";

/** Una línea del desglose de una categoría (para el tooltip). */
export interface Desglose {
  nombre: string;
  total: string;
  porcentaje: string;
}

export interface FilaCategoria {
  id: number;
  nombre: string;
  valor: number;        // SOLO para el largo de la barra
  total: string;        // para mostrar
  porcentaje: string;   // de la API
  color: string;
  desglose: Desglose[];
}

export function prepararCategorias(categorias: TotalCategoria[], colores: Map<number, string>): FilaCategoria[] {
  return categorias.map((c) => {
    const desglose: Desglose[] = c.subcategorias.map((s) => ({ nombre: s.nombre, total: s.total, porcentaje: s.porcentaje }));
    // Si además tiene movimientos en la raíz misma, se muestran como "(directo)", igual que en la tabla.
    if (c.subcategorias.length > 0 && c.directo !== "0.00") {
      desglose.push({ nombre: `${c.nombre} (directo)`, total: c.directo, porcentaje: c.porcentaje_directo });
    }
    return {
      id: c.id_categoria,
      nombre: c.nombre,
      valor: Number(c.total),
      total: c.total,
      porcentaje: c.porcentaje,
      color: colores.get(c.id_categoria) ?? COLOR_SIN_COLOR,
      desglose,
    };
  });
}

export interface FilaMes {
  etiqueta: string;       // "jun"
  etiquetaLarga: string;  // "junio 2026"
  ingresos: number;       // SOLO para dibujar
  egresos: number;
  balance: number;
  textos: { ingresos: string; egresos: string; balance: string };
}

export function prepararMeses(meses: TotalMes[]): FilaMes[] {
  return meses.map((m) => ({
    etiqueta: formatearMes(m.mes),
    etiquetaLarga: formatearMes(m.mes, true),
    ingresos: Number(m.ingresos),
    egresos: Number(m.egresos),
    balance: Number(m.balance),
    textos: { ingresos: m.ingresos, egresos: m.egresos, balance: m.balance },
  }));
}

export interface FilaMeta {
  id: number;
  nombre: string;
  valor: number;          // porcentaje con tope de 100, SOLO para el largo de la barra
  porcentaje: string;     // el real, de la API (puede pasar de 100)
  valorActual: string;
  objetivo: string;
  fecha: string | null;
  cumplida: boolean;
  color: string;
}

/** Solo los bolsillos activos con meta (RN-41). El color sigue al bolsillo (orden de creación). */
export function prepararMetas(bolsillos: Bolsillo[], colores: Map<number, string>): FilaMeta[] {
  return bolsillos
    .filter((b) => b.activo && b.es_meta && b.monto_objetivo !== null && b.progreso_porcentaje !== null)
    .map((b) => {
      const porcentaje = b.progreso_porcentaje as string;
      return {
        id: b.id_bolsillo,
        nombre: b.nombre,
        valor: Math.min(100, Number(porcentaje)),
        porcentaje,
        valorActual: b.valor_actual,
        objetivo: b.monto_objetivo as string,
        fecha: b.fecha_objetivo,
        cumplida: Number(porcentaje) >= 100,
        color: colores.get(b.id_bolsillo) ?? COLOR_SIN_COLOR,
      };
    });
}
