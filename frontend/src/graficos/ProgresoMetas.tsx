// Progreso de los bolsillos con meta: valor actual, objetivo y porcentaje (este, de la API).
// La barra llega como máximo al 100 %; el texto muestra el porcentaje real (puede pasar de 100).
//
// Variantes:
//   A  Barras horizontales con pista gris; nombre y cifras encima de cada barra.
//   B  Anillos concéntricos (uno por meta) con la lista de metas al lado.
//   C  Tarjetas, cada una con su barra; el detalle aparece al pasar el mouse o al tocar.
import { Bar, BarChart, Cell, LabelList, PolarAngleAxis, RadialBar, RadialBarChart, Tooltip, XAxis, YAxis } from "recharts";

import { formatearDinero, formatearPorcentaje } from "../util/formato";
import { COLOR_PISTA, COLOR_SUAVE, COLOR_TEXTO } from "./colores";
import type { FilaMeta } from "./datos";
import { ContenidoMeta, TooltipMeta, type PropsTooltip } from "./Tooltips";
import { ANCHO_ANGOSTO, useAncho } from "./useAncho";

export type VarianteMetas = "A" | "B" | "C";

export function ProgresoMetas({ filas, variante }: { filas: FilaMeta[]; variante: VarianteMetas }) {
  if (filas.length === 0) return <p className="vacio">No hay bolsillos con meta.</p>;
  if (variante === "B") return <MetasAnillos filas={filas} />;
  if (variante === "C") return <MetasTarjetas filas={filas} />;
  return <MetasBarras filas={filas} />;
}

const tooltipMeta = (p: { active?: boolean; payload?: unknown }) => (
  <TooltipMeta active={p.active} payload={p.payload as PropsTooltip<FilaMeta>["payload"]} />
);

function MetasBarras({ filas }: { filas: FilaMeta[] }) {
  const { ref, ancho } = useAncho<HTMLDivElement>();
  const angosto = ancho < ANCHO_ANGOSTO;
  const alturaFila = angosto ? 68 : 52;   // en celular, los montos van en una segunda línea
  const margen = { top: 8, right: 2, bottom: 0, left: 2 };
  const fin = ancho - margen.right;

  function Etiqueta(props: { x?: unknown; y?: unknown; height?: unknown; index?: number }) {
    const meta = filas[props.index ?? 0];
    if (!meta) return null;
    const x = Number(props.x);
    const y = Number(props.y);
    const montos = `${formatearDinero(meta.valorActual)} de ${formatearDinero(meta.objetivo)}`;
    const porcentaje = formatearPorcentaje(meta.porcentaje) + (meta.cumplida ? " ✓" : "");
    return (
      <g>
        <text x={x} y={y - 7} fill={COLOR_TEXTO} fontSize={13}>{meta.nombre}</text>
        <text x={fin} y={y - 7} fill={COLOR_TEXTO} fontSize={13} textAnchor="end" className="cifra-svg">
          {angosto ? porcentaje : <>{montos} <tspan fill={COLOR_SUAVE}>· {porcentaje}</tspan></>}
        </text>
        {angosto && (
          <text x={x} y={y + Number(props.height) + 15} fill={COLOR_SUAVE} fontSize={12} className="cifra-svg">{montos}</text>
        )}
      </g>
    );
  }

  return (
    <div ref={ref} className="grafico">
      {ancho > 0 && (
        <BarChart width={ancho} height={filas.length * alturaFila + margen.top} data={filas} layout="vertical" margin={margen}>
          <XAxis type="number" hide domain={[0, 100]} />
          <YAxis type="category" dataKey="nombre" hide />
          <Tooltip cursor={false} content={tooltipMeta} />
          <Bar dataKey="valor" barSize={12} radius={4} background={{ fill: COLOR_PISTA, radius: 4 }}>
            {filas.map((f) => <Cell key={f.id} fill={f.color} />)}
            <LabelList dataKey="valor" content={(p) => <Etiqueta {...p} />} />
          </Bar>
        </BarChart>
      )}
    </div>
  );
}

function MetasAnillos({ filas }: { filas: FilaMeta[] }) {
  const tamano = 220;
  return (
    <div className="dona">
      <div className="dona-grafico" style={{ width: tamano, height: tamano }}>
        <RadialBarChart width={tamano} height={tamano} data={filas} innerRadius={46} outerRadius={106}
                        startAngle={90} endAngle={-270} barSize={12}>
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="valor" background={{ fill: COLOR_PISTA }} cornerRadius={6}>
            {filas.map((f) => <Cell key={f.id} fill={f.color} />)}
          </RadialBar>
          <Tooltip cursor={false} content={tooltipMeta} />
        </RadialBarChart>
      </div>
      <ul className="leyenda-dona">
        {filas.map((f) => (
          <li key={f.id}>
            <span className="punto" style={{ background: f.color }} />
            <span className="leyenda-nombre">{f.nombre}</span>
            <span className="numero">{formatearPorcentaje(f.porcentaje)}</span>
            <span className="numero suave">{formatearDinero(f.valorActual)} de {formatearDinero(f.objetivo)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MetasTarjetas({ filas }: { filas: FilaMeta[] }) {
  return (
    <ul className="metas-tarjetas">
      {filas.map((f) => (
        // tabIndex: con el teclado (o tocándola en el celular) también se ve el detalle.
        <li key={f.id} className="meta-tarjeta" tabIndex={0}>
          <div className="meta-cabecera">
            <span>{f.nombre}</span>
            <strong className="numero">{formatearPorcentaje(f.porcentaje)}{f.cumplida ? " ✓" : ""}</strong>
          </div>
          <div className="barra">
            <div className="relleno" style={{ width: `${f.valor}%`, background: f.color }} />
          </div>
          <span className="ayuda numero">{formatearDinero(f.valorActual)} de {formatearDinero(f.objetivo)}</span>
          <div className="meta-flotante" role="tooltip">
            <ContenidoMeta meta={f} />
          </div>
        </li>
      ))}
    </ul>
  );
}
