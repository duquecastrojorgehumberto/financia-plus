// Ingresos vs egresos de los últimos meses: barras agrupadas por mes, con UN solo eje Y en
// pesos, cuadrícula horizontal punteada y leyenda arriba. Ingresos y egresos usan los dos
// primeros colores de la paleta (no verde y rojo). Las cifras exactas, en el tooltip.
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";

import { formatearEjeDinero } from "../util/formato";
import { debeAnimar } from "./animacion";
import { marcasDelEje } from "./eje";
import { COLOR_CUADRICULA, COLOR_EGRESOS, COLOR_INGRESOS, COLOR_PISTA, COLOR_SUAVE } from "./colores";
import type { FilaMes } from "./datos";
import { TooltipMes, type PropsTooltip } from "./Tooltips";
import { ANCHO_ANGOSTO, useAncho } from "./useAncho";

/** Una marca del eje Y ("$ 750 mil") en UNA línea (Recharts parte los textos largos en dos). */
function MarcaEje(props: { x?: unknown; y?: unknown; payload?: { value?: unknown } }) {
  return (
    <text x={Number(props.x) - 4} y={Number(props.y)} dy={4} textAnchor="end" fill={COLOR_SUAVE} fontSize={12}>
      {formatearEjeDinero(Number(props.payload?.value ?? 0))}
    </text>
  );
}

/** Leyenda propia, en orden fijo (Recharts la ordena alfabéticamente: Egresos antes que Ingresos). */
export function LeyendaMensual() {
  return (
    <ul className="leyenda-series">
      <li><span className="punto" style={{ background: COLOR_INGRESOS }} />Ingresos</li>
      <li><span className="punto" style={{ background: COLOR_EGRESOS }} />Egresos</li>
    </ul>
  );
}

export function GraficoMensual({ filas }: { filas: FilaMes[] }) {
  const { ref, ancho } = useAncho<HTMLDivElement>();
  const angosto = ancho < ANCHO_ANGOSTO;
  const animar = debeAnimar();
  const marcas = marcasDelEje(Math.max(0, ...filas.flatMap((f) => [f.ingresos, f.egresos])));

  return (
    <div ref={ref} className="grafico">
      {ancho > 0 && (
        <BarChart width={ancho} height={angosto ? 240 : 290} data={filas}
                  margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barGap={2}
                  barCategoryGap={angosto ? "16%" : "26%"}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={COLOR_CUADRICULA} />
          <XAxis dataKey="etiqueta" tickLine={false} axisLine={false} tick={{ fill: COLOR_SUAVE, fontSize: 12 }} />
          <YAxis width={angosto ? 62 : 72} tickLine={false} axisLine={false}
                 ticks={marcas} domain={[0, marcas[marcas.length - 1]]}
                 tick={(p) => <MarcaEje {...p} />} />
          <Tooltip cursor={{ fill: COLOR_PISTA, opacity: 0.7 }}
                   content={(p) => <TooltipMes active={p.active} payload={p.payload as PropsTooltip<FilaMes>["payload"]} />} />
          <Legend verticalAlign="top" height={34} content={() => <LeyendaMensual />} />
          <Bar dataKey="ingresos" name="Ingresos" fill={COLOR_INGRESOS} radius={[4, 4, 0, 0]} maxBarSize={20}
               isAnimationActive={animar} />
          <Bar dataKey="egresos" name="Egresos" fill={COLOR_EGRESOS} radius={[4, 4, 0, 0]} maxBarSize={20}
               isAnimationActive={animar} />
        </BarChart>
      )}
    </div>
  );
}
