// Ingresos vs egresos de los últimos meses: barras agrupadas por mes, UN solo eje Y en pesos.
// Ingresos y egresos usan los dos primeros colores de la paleta (no verde y rojo).
//
// Variantes:
//   A  Cuadrícula horizontal punteada, eje con montos abreviados y leyenda arriba.
//   B  Minimalista: sin cuadrícula ni eje, barras más anchas, leyenda abajo (las cifras, en el tooltip).
//   C  Como A, más una línea con el balance de cada mes y la línea del cero.
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";

import { formatearEjeDinero } from "../util/formato";
import { COLOR_BALANCE, COLOR_CUADRICULA, COLOR_EGRESOS, COLOR_INGRESOS, COLOR_PISTA, COLOR_SUAVE } from "./colores";
import type { FilaMes } from "./datos";
import { TooltipMes, type PropsTooltip } from "./Tooltips";
import { ANCHO_ANGOSTO, useAncho } from "./useAncho";

export type VarianteMensual = "A" | "B" | "C";

/** Una marca del eje Y ("$ 750 mil") en UNA línea (Recharts parte los textos largos en dos). */
function MarcaEje(props: { x?: unknown; y?: unknown; payload?: { value?: unknown } }) {
  return (
    <text x={Number(props.x) - 4} y={Number(props.y)} dy={4} textAnchor="end" fill={COLOR_SUAVE} fontSize={12}>
      {formatearEjeDinero(Number(props.payload?.value ?? 0))}
    </text>
  );
}

/** Leyenda propia: Recharts ordena las series alfabéticamente (Egresos antes que Ingresos). */
function Leyenda({ conBalance, centrada }: { conBalance: boolean; centrada: boolean }) {
  const series = [
    { nombre: "Ingresos", color: COLOR_INGRESOS },
    { nombre: "Egresos", color: COLOR_EGRESOS },
    ...(conBalance ? [{ nombre: "Balance", color: COLOR_BALANCE }] : []),
  ];
  return (
    <ul className={centrada ? "leyenda-series centrada" : "leyenda-series"}>
      {series.map((s) => (
        <li key={s.nombre}>
          <span className="punto" style={{ background: s.color }} />
          {s.nombre}
        </li>
      ))}
    </ul>
  );
}

export function GraficoMensual({ filas, variante }: { filas: FilaMes[]; variante: VarianteMensual }) {
  const { ref, ancho } = useAncho<HTMLDivElement>();
  const angosto = ancho < ANCHO_ANGOSTO;
  const minimalista = variante === "B";

  return (
    <div ref={ref} className="grafico">
      {ancho > 0 && (
        <ComposedChart width={ancho} height={angosto ? 240 : 290} data={filas}
                       margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barGap={2}
                       barCategoryGap={angosto ? "16%" : "26%"}>
          {!minimalista && <CartesianGrid vertical={false} strokeDasharray="3 3" stroke={COLOR_CUADRICULA} />}
          <XAxis dataKey="etiqueta" tickLine={false} axisLine={false} tick={{ fill: COLOR_SUAVE, fontSize: 12 }} />
          <YAxis hide={minimalista} width={angosto ? 62 : 72} tickLine={false} axisLine={false} tickCount={4}
                 tick={(p) => <MarcaEje {...p} />} />
          <Tooltip cursor={{ fill: COLOR_PISTA, opacity: 0.7 }}
                   content={(p) => <TooltipMes active={p.active} payload={p.payload as PropsTooltip<FilaMes>["payload"]} />} />
          <Legend verticalAlign={minimalista ? "bottom" : "top"} height={34}
                  content={() => <Leyenda conBalance={variante === "C"} centrada={minimalista} />} />
          {variante === "C" && <ReferenceLine y={0} stroke={COLOR_SUAVE} strokeOpacity={0.6} />}
          <Bar dataKey="ingresos" name="Ingresos" fill={COLOR_INGRESOS} radius={[4, 4, 0, 0]}
               maxBarSize={minimalista ? 30 : 20} />
          <Bar dataKey="egresos" name="Egresos" fill={COLOR_EGRESOS} radius={[4, 4, 0, 0]}
               maxBarSize={minimalista ? 30 : 20} />
          {variante === "C" && (
            <Line dataKey="balance" name="Balance" type="linear" stroke={COLOR_BALANCE} strokeWidth={2}
                  dot={{ r: 3, fill: COLOR_BALANCE, strokeWidth: 0 }} activeDot={{ r: 5 }} />
          )}
        </ComposedChart>
      )}
    </div>
  );
}
