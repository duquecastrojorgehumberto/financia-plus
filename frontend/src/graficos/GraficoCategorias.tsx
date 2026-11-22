// Egresos (o ingresos) por categoría: barras horizontales de mayor a menor, con el
// monto y el porcentaje al final. El orden ya viene de la API (de mayor a menor).
//
// Variantes (la galería las muestra todas; se elige una):
//   A  Nombre a la izquierda y cifras al final de la barra, sin cuadrícula.
//   B  Nombre y cifras ENCIMA de una barra delgada, que usa todo el ancho.
//   C  Como A, pero cada barra sobre una "pista" gris y con cuadrícula suave.
// En pantallas angostas (celular), todas ponen el nombre encima para dejar espacio a la barra.
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { formatearDinero, formatearPorcentajeExacto } from "../util/formato";
import { COLOR_CUADRICULA, COLOR_PISTA, COLOR_SUAVE, COLOR_TEXTO } from "./colores";
import type { FilaCategoria } from "./datos";
import { TooltipCategoria, type PropsTooltip } from "./Tooltips";
import { ANCHO_ANGOSTO, useAncho } from "./useAncho";

export type VarianteCategorias = "A" | "B" | "C";

/** El nombre de la categoría en el eje, en UNA línea (Recharts parte los nombres largos en dos). */
function NombreEnEje(props: { x?: unknown; y?: unknown; payload?: { value?: unknown } }) {
  return (
    <text x={Number(props.x) - 4} y={Number(props.y)} dy={4} textAnchor="end" fill={COLOR_TEXTO} fontSize={13}>
      {String(props.payload?.value ?? "")}
    </text>
  );
}

const ANCHO_NOMBRES = 170;   // columna de nombres (variantes A y C en pantalla ancha)
const ANCHO_CIFRAS = 160;    // espacio a la derecha para "$ 1.250.000 · 55,1 %"

interface Propiedades {
  filas: FilaCategoria[];
  variante: VarianteCategorias;
}

export function GraficoCategorias({ filas, variante }: Propiedades) {
  const { ref, ancho } = useAncho<HTMLDivElement>();
  const encima = variante === "B" || ancho < ANCHO_ANGOSTO;
  const conPista = variante === "C";

  const alturaFila = encima ? 50 : 38;
  const margen = encima
    ? { top: 8, right: 2, bottom: 0, left: 2 }
    : { top: 4, right: ANCHO_CIFRAS, bottom: 4, left: 2 };
  const alto = filas.length * alturaFila + margen.top + margen.bottom;
  const finDelArea = ancho - margen.right;   // borde derecho donde terminan las barras

  /** Las etiquetas de cada barra: dónde van depende de la variante. */
  function Etiqueta(props: { x?: unknown; y?: unknown; width?: unknown; height?: unknown; index?: number }) {
    const fila = filas[props.index ?? 0];
    if (!fila) return null;
    const x = Number(props.x);
    const y = Number(props.y);
    const largo = Number(props.width);
    const grosor = Number(props.height);
    const monto = formatearDinero(fila.total);
    const porcentaje = formatearPorcentajeExacto(fila.porcentaje);

    if (encima) {
      // Nombre a la izquierda y cifras a la derecha, sobre la barra.
      return (
        <g>
          <text x={x} y={y - 7} fill={COLOR_TEXTO} fontSize={13}>{fila.nombre}</text>
          <text x={finDelArea} y={y - 7} fill={COLOR_TEXTO} fontSize={13} textAnchor="end" className="cifra-svg">
            {monto} <tspan fill={COLOR_SUAVE}>· {porcentaje}</tspan>
          </text>
        </g>
      );
    }
    // A: justo después de la barra. C: después de la pista (todas alineadas).
    const inicio = conPista ? finDelArea + 10 : x + largo + 8;
    return (
      <text x={inicio} y={y + grosor / 2} dominantBaseline="central" fill={COLOR_TEXTO} fontSize={13} className="cifra-svg">
        {monto} <tspan fill={COLOR_SUAVE}>· {porcentaje}</tspan>
      </text>
    );
  }

  return (
    <div ref={ref} className="grafico">
      {ancho > 0 && filas.length > 0 && (
        <BarChart width={ancho} height={alto} data={filas} layout="vertical" margin={margen}>
          {conPista && !encima && (
            <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke={COLOR_CUADRICULA} />
          )}
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis type="category" dataKey="nombre" hide={encima} width={ANCHO_NOMBRES}
                 tickLine={false} axisLine={false} tick={(p) => <NombreEnEje {...p} />} />
          <Tooltip cursor={{ fill: COLOR_PISTA, opacity: 0.7 }}
                   content={(p) => <TooltipCategoria active={p.active}
                                                     payload={p.payload as PropsTooltip<FilaCategoria>["payload"]} />} />
          <Bar dataKey="valor" barSize={encima ? 10 : conPista ? 16 : 14} radius={4}
               background={conPista ? { fill: COLOR_PISTA, radius: 4 } : undefined}>
            {filas.map((f) => <Cell key={f.id} fill={f.color} />)}
            <LabelList dataKey="valor" content={(p) => <Etiqueta {...p} />} />
          </Bar>
        </BarChart>
      )}
    </div>
  );
}
