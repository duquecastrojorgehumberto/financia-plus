// Qué categorías ofrecer en un formulario.
import type { RamaCategoria } from "../api/tipos";

/**
 * Solo las activas (RN-25: una desactivada no se usa en un movimiento nuevo).
 * Al corregir, también la que el movimiento ya tiene (idActual): la API la
 * conserva aunque se haya desactivado después, si no se cambia.
 */
export function ramasUtilizables(ramas: RamaCategoria[], idActual?: number | null): RamaCategoria[] {
  const sirve = (c: { id_categoria: number; activa: boolean }) => c.activa || c.id_categoria === idActual;
  return ramas
    .filter((r) => sirve(r) || r.subcategorias.some((s) => s.id_categoria === idActual))
    .map((r) => ({ ...r, subcategorias: r.subcategorias.filter(sirve) }));
}
