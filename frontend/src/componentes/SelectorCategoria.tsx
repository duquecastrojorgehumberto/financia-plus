// Lista desplegable de categorías: cada raíz y, debajo, sus subcategorías
// ("Alimentación › Mercado"). La raíz también se puede elegir: un movimiento
// puede ir directo a ella (RN-27). Se reutiliza en el formulario y en los filtros.
import type { RamaCategoria } from "../api/tipos";

interface Propiedades {
  etiqueta: string;
  ramas: RamaCategoria[];
  valor: number | "";
  alCambiar: (idCategoria: number | "") => void;
  /** Texto de la opción vacía (por ejemplo "Todas"). Sin él, el campo es obligatorio. */
  opcionVacia?: string;
  deshabilitado?: boolean;
}

export function SelectorCategoria({ etiqueta, ramas, valor, alCambiar, opcionVacia, deshabilitado }: Propiedades) {
  return (
    <label>
      {etiqueta}
      <select value={valor} disabled={deshabilitado} required={opcionVacia === undefined}
              onChange={(e) => alCambiar(e.target.value === "" ? "" : Number(e.target.value))}>
        <option value="">{opcionVacia ?? "Elija una categoría"}</option>
        {ramas.map((r) => [
          <option key={r.id_categoria} value={r.id_categoria}>
            {r.nombre}{r.activa ? "" : " (desactivada)"}
          </option>,
          ...r.subcategorias.map((s) => (
            <option key={s.id_categoria} value={s.id_categoria}>
              {r.nombre} › {s.nombre}{s.activa ? "" : " (desactivada)"}
            </option>
          )),
        ])}
      </select>
    </label>
  );
}
