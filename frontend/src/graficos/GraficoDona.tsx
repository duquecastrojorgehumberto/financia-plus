// Distribución de egresos: anillo delgado con esquinas redondeadas y el total en el centro,
// con la leyenda al lado (nombre, porcentaje y monto de cada categoría, mismos colores que
// las barras). En pantallas angostas la leyenda baja debajo del anillo.
import { Cell, Pie, PieChart, Tooltip } from "recharts";

import { formatearDinero, formatearPorcentajeExacto } from "../util/formato";
import { debeAnimar } from "./animacion";
import type { FilaCategoria } from "./datos";
import { TooltipCategoria, type PropsTooltip } from "./Tooltips";

const TAMANO = 220;

interface Propiedades {
  filas: FilaCategoria[];
  total: string;   // el total de egresos del periodo, de la API
}

export function GraficoDona({ filas, total }: Propiedades) {
  return (
    <div className="dona">
      <div className="dona-grafico" style={{ width: TAMANO, height: TAMANO }}>
        <PieChart width={TAMANO} height={TAMANO}>
          <Pie data={filas} dataKey="valor" nameKey="nombre" startAngle={90} endAngle={-270}
               innerRadius={82} outerRadius={100} paddingAngle={2} cornerRadius={4} strokeWidth={0}
               isAnimationActive={debeAnimar()}>
            {filas.map((f) => <Cell key={f.id} fill={f.color} />)}
          </Pie>
          <Tooltip content={(p) => <TooltipCategoria active={p.active}
                                                     payload={p.payload as PropsTooltip<FilaCategoria>["payload"]} />} />
        </PieChart>
        <div className="dona-centro">
          <span>Egresos</span>
          <strong>{formatearDinero(total)}</strong>
        </div>
      </div>
      <ul className="leyenda-dona">
        {filas.map((f) => (
          <li key={f.id}>
            <span className="punto" style={{ background: f.color }} />
            <span className="leyenda-nombre">{f.nombre}</span>
            <span className="numero">{formatearPorcentajeExacto(f.porcentaje)}</span>
            <span className="numero suave">{formatearDinero(f.total)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
