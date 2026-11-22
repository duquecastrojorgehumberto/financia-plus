// Distribución de egresos: gráfico de dona con el total en el centro y una leyenda
// con el nombre, el porcentaje y el monto de cada categoría (mismos colores que las barras).
//
// Variantes:
//   A  Anillo grueso con separación blanca entre porciones; leyenda en lista a un lado.
//   B  Anillo delgado con esquinas redondeadas y espacio entre porciones; leyenda en dos columnas debajo.
import { Cell, Pie, PieChart, Tooltip } from "recharts";

import { formatearDinero, formatearPorcentajeExacto } from "../util/formato";
import type { FilaCategoria } from "./datos";
import { TooltipCategoria, type PropsTooltip } from "./Tooltips";

export type VarianteDona = "A" | "B";

const TAMANO = 220;

interface Propiedades {
  filas: FilaCategoria[];
  total: string;   // el total de egresos del periodo, de la API
  variante: VarianteDona;
}

export function GraficoDona({ filas, total, variante }: Propiedades) {
  const delgada = variante === "B";
  return (
    <div className={delgada ? "dona dona-abajo" : "dona"}>
      <div className="dona-grafico" style={{ width: TAMANO, height: TAMANO }}>
        <PieChart width={TAMANO} height={TAMANO}>
          <Pie data={filas} dataKey="valor" nameKey="nombre" startAngle={90} endAngle={-270}
               innerRadius={delgada ? 82 : 64} outerRadius={delgada ? 100 : 104}
               paddingAngle={delgada ? 2 : 0} cornerRadius={delgada ? 4 : 0}
               stroke="#ffffff" strokeWidth={delgada ? 0 : 2}>
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
