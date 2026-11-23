// Progreso de los bolsillos con meta, en tarjetas: nombre, porcentaje, barra y "lo que tiene
// de la meta". Al pasar el mouse, al enfocar con el teclado o al tocar, aparece el detalle.
// El porcentaje viene de la API (RN-48); la barra llega como máximo al 100 %, el texto
// muestra el real (puede pasar de 100).
import { formatearDinero, formatearPorcentaje } from "../util/formato";
import type { FilaMeta } from "./datos";
import { ContenidoMeta } from "./Tooltips";

export function ProgresoMetas({ filas }: { filas: FilaMeta[] }) {
  if (filas.length === 0) return <p className="vacio">No hay bolsillos con meta.</p>;
  return (
    <ul className="metas-tarjetas">
      {filas.map((f) => (
        // tabIndex: con el teclado (o tocándola en el celular) también se ve el detalle.
        <li key={f.id} className="meta-tarjeta" tabIndex={0}>
          <div className="meta-cabecera">
            <span>{f.nombre}</span>
            <strong className="numero">{formatearPorcentaje(f.porcentaje)}{f.cumplida ? " ✓" : ""}</strong>
          </div>
          <div className="barra" role="progressbar" aria-valuenow={f.valor} aria-valuemin={0} aria-valuemax={100}
               aria-label={`${f.nombre}: ${formatearPorcentaje(f.porcentaje)}`}>
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
