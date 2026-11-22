// Llamadas a las categorías (app/rutas/categorias.py). Una función por ruta de la API.
import { api } from "./cliente";
import type { Categoria, RamaCategoria, TipoCategoria } from "./tipos";

/** El árbol de un tipo. Sin inactivas, la API devuelve solo las activas. */
export async function listarCategorias(tipo: TipoCategoria, incluirInactivas = false): Promise<RamaCategoria[]> {
  const parametros = new URLSearchParams({ tipo });
  if (incluirInactivas) parametros.set("inactivas", "1");
  return (await api.get<{ categorias: RamaCategoria[] }>(`/categorias?${parametros}`)).categorias;
}

/** Una categoría raíz: lleva su tipo. */
export async function crearCategoria(nombre: string, tipo: TipoCategoria): Promise<Categoria> {
  return (await api.post<{ categoria: Categoria }>("/categorias", { nombre, tipo })).categoria;
}

/** Una subcategoría: el tipo lo toma de su padre (RN-23), por eso no se envía. */
export async function crearSubcategoria(nombre: string, idPadre: number): Promise<Categoria> {
  return (await api.post<{ categoria: Categoria }>("/categorias", { nombre, id_padre: idPadre })).categoria;
}

/** Solo el nombre se puede cambiar (RN-22). */
export async function renombrarCategoria(idCategoria: number, nombre: string): Promise<Categoria> {
  return (await api.put<{ categoria: Categoria }>(`/categorias/${idCategoria}`, { nombre })).categoria;
}

/** Desactivar una raíz desactiva también sus subcategorías (RN-25); la API dice cuántas. */
export async function desactivarCategoria(idCategoria: number): Promise<number> {
  const respuesta = await api.post<{ categoria: Categoria; subcategorias_desactivadas: number }>(
    `/categorias/${idCategoria}/desactivar`,
  );
  return respuesta.subcategorias_desactivadas;
}

/** Reactiva solo esta categoría; una subcategoría necesita a su padre activo. */
export async function reactivarCategoria(idCategoria: number): Promise<Categoria> {
  return (await api.post<{ categoria: Categoria }>(`/categorias/${idCategoria}/reactivar`)).categoria;
}
