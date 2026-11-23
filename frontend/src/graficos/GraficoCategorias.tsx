// Egresos (o ingresos) por categoría: barras horizontales de mayor a menor.
// Encima de cada barra van el nombre (a la izquierda) y el monto con su porcentaje
// (a la derecha); así la barra usa todo el ancho, también en el celular.
// El orden (de mayor a menor) y los porcentajes vienen de la API.
import { Bar, BarChart, Cell, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import { formatearDinero, formatearPorcentajeExacto } from "../util/formato";
import { debeAnimar } from "./animacion";
import { COLOR_PISTA, COLOR_SUAVE, COLOR_TEXTO } from "./colores";
import type { FilaCategoria } from "./datos";
import { TooltipCategoria, type PropsTooltip } from "./Tooltips";
import { useAncho } from "./useAncho";

const ALTURA_FILA = 50;   // espacio de cada categoría: textos encima + barra
const MARGEN = { top: 8, right: 2, bottom: 0, left: 2 };

export function GraficoCategorias({ filas }: { filas: FilaCategoria[] }) {
  const { ref, ancho } = useAncho<HTMLDivElement>();
  const finDelArea = ancho - MARGEN.right;   // borde derecho, donde se alinean las cifras

  /** Los textos de cada barra: el nombre a la izquierda y las cifras a la derecha, encima de la barra. */
  function Etiqueta(props: { x?: unknown; y?: unknown; index?: number }) {
    const fila = filas[props.index ?? 0];
    if (!fila) return null;
    const x = Number(props.x);
    const y = Number(props.y) - 7;
    return (
      <g>
        <text x={x} y={y} fill={COLOR_TEXTO} fontSize={13}>{fila.nombre}</text>
        <text x={finDelArea} y={y} fill={COLOR_TEXTO} fontSize={13} textAnchor="end" className="cifra-svg">
          {formatearDinero(fila.total)} <tspan fill={COLOR_SUAVE}>· {formatearPorcentajeExacto(fila.porcentaje)}</tspan>
        </text>
      </g>
    );
  }

  return (
    <div ref={ref} className="grafico">
      {ancho > 0 && filas.length > 0 && (
        <BarChart width={ancho} height={filas.length * ALTURA_FILA + MARGEN.top} data={filas}
                  layout="vertical" margin={MARGEN}>
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis type="category" dataKey="nombre" hide />
          <Tooltip cursor={{ fill: COLOR_PISTA, opacity: 0.7 }}
                   content={(p) => <TooltipCategoria active={p.active}
                                                     payload={p.payload as PropsTooltip<FilaCategoria>["payload"]} />} />
          <Bar dataKey="valor" barSize={10} radius={4} isAnimationActive={debeAnimar()}>
            {filas.map((f) => <Cell key={f.id} fill={f.color} />)}
            <LabelList dataKey="valor" content={(p) => <Etiqueta {...p} />} />
          </Bar>
        </BarChart>
      )}
    </div>
  );
}
