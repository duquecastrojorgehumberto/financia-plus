// Tipos de TypeScript con la forma EXACTA del JSON que responde la API.
// Cada uno corresponde a un datos_publicos() del servidor (app/entidades y app/servicios).
//
// El dinero llega como TEXTO ("130000.00"), nunca como número: así no se pierden
// centavos (RNF-08). Para mostrarlo se usa formatearDinero (src/util/formato.ts).
// Las fechas llegan como texto "AAAA-MM-DD".

/** Texto con un valor de dinero, por ejemplo "130000.00" o "-50000.00". */
export type Dinero = string;

export interface Usuario {
  id_usuario: number;
  nombre: string;
  correo: string;
}

export interface RespuestaUsuario {
  usuario: Usuario;
}

/** RN-60 a RN-63. */
export interface Indicadores {
  saldo_total: Dinero;
  total_reservado: Dinero;
  disponible: Dinero;
  disponible_negativo: boolean;
}

export interface TotalSubcategoria {
  id_categoria: number;
  nombre: string;
  total: Dinero;
}

/** Una categoría raíz con su total consolidado (RN-27): total = directo + subcategorías. */
export interface TotalCategoria {
  id_categoria: number;
  nombre: string;
  total: Dinero;
  directo: Dinero;
  subcategorias: TotalSubcategoria[];
}

export interface ResumenPeriodo {
  desde: string;
  hasta: string;
  ingresos: Dinero;
  egresos: Dinero;
  balance: Dinero;
  ajustes: { aumentos: Dinero; disminuciones: Dinero };
  categorias: { ingresos: TotalCategoria[]; egresos: TotalCategoria[] };
}

export interface RespuestaResumen {
  indicadores: Indicadores;
  periodo: ResumenPeriodo;
}
