// Los recuadros que aparecen al pasar el mouse (o tocar) un gráfico.
// Todas las cifras se muestran desde el TEXTO de la API, con formatearDinero.
import type { ReactNode } from "react";

import { formatearDinero, formatearFecha, formatearPorcentaje, formatearPorcentajeExacto } from "../util/formato";
import { COLOR_BALANCE, COLOR_EGRESOS, COLOR_INGRESOS } from "./colores";
import type { FilaCategoria, FilaMes, FilaMeta } from "./datos";

/** Lo que Recharts le pasa al contenido del tooltip (solo lo que se usa aquí). */
export interface PropsTooltip<T> {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: T }>;
}

function Recuadro({ titulo, color, children }: { titulo: string; color?: string; children: ReactNode }) {
  return (
    <div className="tooltip-grafico">
      <div className="tooltip-titulo">
        {color && <span className="punto" style={{ background: color }} />}
        {titulo}
      </div>
      {children}
    </div>
  );
}

function Linea({ nombre, valor, color, suave = false }: { nombre: string; valor: string; color?: string; suave?: boolean }) {
  return (
    <div className={suave ? "tooltip-linea suave" : "tooltip-linea"}>
      <span>
        {color && <span className="punto" style={{ background: color }} />}
        {nombre}
      </span>
      <span className="numero">{valor}</span>
    </div>
  );
}

/** Categoría: monto, porcentaje y el desglose por subcategoría. */
export function TooltipCategoria({ active, payload }: PropsTooltip<FilaCategoria>) {
  const fila = payload?.[0]?.payload;
  if (!active || !fila) return null;
  return (
    <Recuadro titulo={fila.nombre} color={fila.color}>
      <Linea nombre="Total" valor={`${formatearDinero(fila.total)} · ${formatearPorcentajeExacto(fila.porcentaje)}`} />
      {fila.desglose.length > 0 && <div className="tooltip-separador" />}
      {fila.desglose.map((d) => (
        <Linea key={d.nombre} nombre={d.nombre} suave
               valor={`${formatearDinero(d.total)} · ${formatearPorcentajeExacto(d.porcentaje)}`} />
      ))}
    </Recuadro>
  );
}

/** Mes: ingresos, egresos y balance. */
export function TooltipMes({ active, payload }: PropsTooltip<FilaMes>) {
  const fila = payload?.[0]?.payload;
  if (!active || !fila) return null;
  return (
    <Recuadro titulo={fila.etiquetaLarga}>
      <Linea nombre="Ingresos" color={COLOR_INGRESOS} valor={formatearDinero(fila.textos.ingresos)} />
      <Linea nombre="Egresos" color={COLOR_EGRESOS} valor={formatearDinero(fila.textos.egresos)} />
      <div className="tooltip-separador" />
      <Linea nombre="Balance" color={COLOR_BALANCE} valor={formatearDinero(fila.textos.balance)} />
    </Recuadro>
  );
}

/** Meta: valor actual, objetivo, porcentaje y fecha. */
export function TooltipMeta({ active, payload }: PropsTooltip<FilaMeta>) {
  const fila = payload?.[0]?.payload;
  if (!active || !fila) return null;
  return <ContenidoMeta meta={fila} />;
}

export function ContenidoMeta({ meta }: { meta: FilaMeta }) {
  return (
    <Recuadro titulo={meta.nombre} color={meta.color}>
      <Linea nombre="Tiene" valor={formatearDinero(meta.valorActual)} />
      <Linea nombre="Meta" valor={formatearDinero(meta.objetivo)} />
      <Linea nombre="Progreso" valor={formatearPorcentaje(meta.porcentaje) + (meta.cumplida ? " · cumplida" : "")} />
      {meta.fecha && <Linea nombre="Para el" valor={formatearFecha(meta.fecha)} suave />}
    </Recuadro>
  );
}
