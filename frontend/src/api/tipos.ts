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

/** Valores permitidos por la base (ck_cuenta_tipo, D-16). */
export type TipoCuenta = "EFECTIVO" | "AHORROS" | "CORRIENTE" | "BILLETERA_DIGITAL" | "OTRA";

/** Una cuenta con su saldo ya calculado por la API (RN-11). */
export interface Cuenta {
  id_cuenta: number;
  nombre: string;
  tipo: TipoCuenta;
  saldo_inicial: Dinero;
  saldo: Dinero;
  saldo_negativo: boolean;   // RN-14: se avisa, no se bloquea
  activa: boolean;           // false = archivada (RN-12)
  creado_en: string;
}

/** Lo que se envía para crear o editar una cuenta. */
export interface DatosCuenta {
  nombre: string;
  tipo: TipoCuenta;
  saldo_inicial: Dinero;
}

/** RN-20. */
export type TipoCategoria = "INGRESO" | "EGRESO";

export interface Categoria {
  id_categoria: number;
  id_padre: number | null;   // null = categoría raíz
  nombre: string;
  tipo: TipoCategoria;
  activa: boolean;           // false = desactivada (RN-25)
}

/** Una categoría raíz con sus subcategorías: el árbol tiene solo dos niveles (RN-21). */
export interface RamaCategoria extends Categoria {
  subcategorias: Categoria[];
}
