// Pantalla de categorías (RF-03): ver el árbol, crear, renombrar, desactivar y reactivar.
//
// Se muestra un tipo a la vez (egresos o ingresos). Cada categoría raíz va en una
// tarjeta con sus subcategorías debajo: solo hay dos niveles (RN-21).
// Lo que la API decide y esta pantalla solo muestra:
//   * Solo cambia el nombre; el tipo y el padre no (RN-22).
//   * La subcategoría toma el tipo de su padre (RN-23).
//   * Nombre único entre hermanas activas (RN-24).
//   * No se borra: se desactiva, y con la raíz se desactivan sus subcategorías (RN-25).
// Después de cada acción se vuelve a pedir el árbol a la API.
import { useEffect, useState, type FormEvent } from "react";

import {
  crearCategoria,
  crearSubcategoria,
  desactivarCategoria,
  listarCategorias,
  reactivarCategoria,
  renombrarCategoria,
} from "../api/categorias";
import { ErrorApi } from "../api/cliente";
import type { Categoria, RamaCategoria, TipoCategoria } from "../api/tipos";

function mensajeDe(e: unknown): string {
  return e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.";
}

export function Categorias() {
  const [tipo, setTipo] = useState<TipoCategoria>("EGRESO");
  const [verInactivas, setVerInactivas] = useState(false);
  const [ramas, setRamas] = useState<RamaCategoria[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupada, setOcupada] = useState<number | null>(null);   // categoría con una acción en curso

  async function cargar() {
    try {
      setRamas(await listarCategorias(tipo, verInactivas));
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    setCargando(true);
    void cargar();
  }, [tipo, verInactivas]);

  function limpiarMensajes() {
    setError(null);
    setAviso(null);
  }

  /** Para crear y renombrar: si la API responde un error, lo muestra el propio formulario. */
  async function guardarYRecargar(accion: () => Promise<unknown>) {
    limpiarMensajes();
    await accion();
    await cargar();
  }

  async function desactivar(categoria: Categoria, subcategoriasActivas: number) {
    if (subcategoriasActivas > 0) {
      const seguir = window.confirm(
        `También se desactivarán sus ${subcategoriasActivas} subcategorías. Si después reactiva ` +
          `"${categoria.nombre}", sus subcategorías no vuelven solas: se reactivan una por una. ¿Continuar?`,
      );
      if (!seguir) return;
    }
    limpiarMensajes();
    setOcupada(categoria.id_categoria);
    try {
      const desactivadas = await desactivarCategoria(categoria.id_categoria);
      setAviso(
        desactivadas > 0
          ? `Se desactivó "${categoria.nombre}" y ${desactivadas} subcategorías. Sus movimientos no cambian.`
          : `Se desactivó "${categoria.nombre}". Sus movimientos no cambian.`,
      );
      await cargar();
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setOcupada(null);
    }
  }

  async function reactivar(categoria: Categoria) {
    limpiarMensajes();
    setOcupada(categoria.id_categoria);
    try {
      await reactivarCategoria(categoria.id_categoria);
      await cargar();
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "Primero reactive la categoría padre."
    } finally {
      setOcupada(null);
    }
  }

  const acciones: Acciones = {
    ocupada,
    renombrar: (c, nombre) => guardarYRecargar(() => renombrarCategoria(c.id_categoria, nombre)),
    agregarSubcategoria: (padre, nombre) => guardarYRecargar(() => crearSubcategoria(nombre, padre.id_categoria)),
    desactivar: (c, subActivas) => void desactivar(c, subActivas),
    reactivar: (c) => void reactivar(c),
  };

  return (
    <section>
      <h1>Categorías</h1>

      <div className="pestanas" role="tablist">
        {(["EGRESO", "INGRESO"] as const).map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tipo === t}
                  className={tipo === t ? "pestana activa" : "pestana"}
                  onClick={() => { limpiarMensajes(); setTipo(t); }}>
            {t === "EGRESO" ? "Egresos" : "Ingresos"}
          </button>
        ))}
      </div>

      <div className="tarjeta formulario-ancho">
        <FormularioNombre
          key={tipo}
          etiqueta={tipo === "EGRESO" ? "Nueva categoría de egreso" : "Nueva categoría de ingreso"}
          textoBoton="Crear"
          alEnviar={(nombre) => guardarYRecargar(() => crearCategoria(nombre, tipo))}
        />
      </div>

      <label className="casilla">
        <input type="checkbox" checked={verInactivas} onChange={(e) => setVerInactivas(e.target.checked)} />
        Mostrar también las categorías desactivadas
      </label>

      {error && <p className="mensaje-error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}

      {cargando ? (
        <p className="cargando">Cargando…</p>
      ) : ramas.length === 0 ? (
        <p className="vacio">No hay categorías de este tipo.</p>
      ) : (
        <div className="lista-tarjetas anchas">
          {ramas.map((r) => (
            <TarjetaRama key={r.id_categoria} rama={r} acciones={acciones} />
          ))}
        </div>
      )}
    </section>
  );
}

/** Lo que cada tarjeta puede pedirle a la pantalla. */
interface Acciones {
  ocupada: number | null;
  renombrar: (categoria: Categoria, nombre: string) => Promise<void>;
  agregarSubcategoria: (padre: Categoria, nombre: string) => Promise<void>;
  desactivar: (categoria: Categoria, subcategoriasActivas: number) => void;
  reactivar: (categoria: Categoria) => void;
}

function TarjetaRama({ rama, acciones }: { rama: RamaCategoria; acciones: Acciones }) {
  const [agregando, setAgregando] = useState(false);
  const subActivas = rama.subcategorias.filter((s) => s.activa).length;
  return (
    <article className={rama.activa ? "tarjeta rama" : "tarjeta rama archivada"}>
      <FilaCategoria categoria={rama} esRaiz acciones={acciones} subcategoriasActivas={subActivas} />

      {rama.subcategorias.length > 0 && (
        <ul className="subcategorias">
          {rama.subcategorias.map((s) => (
            <li key={s.id_categoria}>
              <FilaCategoria categoria={s} esRaiz={false} acciones={acciones} subcategoriasActivas={0} />
            </li>
          ))}
        </ul>
      )}

      {rama.activa &&
        (agregando ? (
          <FormularioNombre
            etiqueta={`Subcategoría de "${rama.nombre}"`}
            textoBoton="Agregar"
            alEnviar={async (nombre) => {
              await acciones.agregarSubcategoria(rama, nombre);
              setAgregando(false);
            }}
            alCancelar={() => setAgregando(false)}
          />
        ) : (
          <button type="button" className="boton-enlace" onClick={() => setAgregando(true)}>
            + Agregar subcategoría
          </button>
        ))}
    </article>
  );
}

interface PropiedadesFila {
  categoria: Categoria;
  esRaiz: boolean;
  subcategoriasActivas: number;
  acciones: Acciones;
}

function FilaCategoria({ categoria, esRaiz, subcategoriasActivas, acciones }: PropiedadesFila) {
  const [renombrando, setRenombrando] = useState(false);
  const ocupada = acciones.ocupada === categoria.id_categoria;

  if (renombrando) {
    return (
      <FormularioNombre
        etiqueta="Nuevo nombre"
        valorInicial={categoria.nombre}
        textoBoton="Guardar"
        alEnviar={async (nombre) => {
          await acciones.renombrar(categoria, nombre);
          setRenombrando(false);
        }}
        alCancelar={() => setRenombrando(false)}
      />
    );
  }

  return (
    <div className={esRaiz ? "fila-categoria raiz" : "fila-categoria"}>
      <span className="nombre-categoria">
        {esRaiz ? <h3>{categoria.nombre}</h3> : categoria.nombre}
        {!categoria.activa && <span className="etiqueta">Desactivada</span>}
      </span>
      <span className="acciones">
        {categoria.activa && (
          <button type="button" className="boton-enlace" onClick={() => setRenombrando(true)} disabled={ocupada}>
            Renombrar
          </button>
        )}
        {categoria.activa ? (
          <button type="button" className="boton-enlace" disabled={ocupada}
                  onClick={() => acciones.desactivar(categoria, subcategoriasActivas)}>
            Desactivar
          </button>
        ) : (
          <button type="button" className="boton-enlace" disabled={ocupada}
                  onClick={() => acciones.reactivar(categoria)}>
            Reactivar
          </button>
        )}
      </span>
    </div>
  );
}

interface PropiedadesFormularioNombre {
  etiqueta: string;
  textoBoton: string;
  valorInicial?: string;
  alEnviar: (nombre: string) => Promise<void>;
  alCancelar?: () => void;
}

/** Formulario de un solo campo (crear, agregar subcategoría, renombrar). Muestra el error de la API. */
function FormularioNombre({ etiqueta, textoBoton, valorInicial = "", alEnviar, alCancelar }: PropiedadesFormularioNombre) {
  const [nombre, setNombre] = useState(valorInicial);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);   // evita el doble envío
    try {
      await alEnviar(nombre);
      setNombre("");
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "Ya existe una categoría activa con ese nombre..."
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="formulario-nombre" onSubmit={enviar}>
      <label>
        {etiqueta}
        <input type="text" value={nombre} required autoFocus={!!alCancelar}
               onChange={(e) => { setNombre(e.target.value); setError(null); }} />
      </label>
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : textoBoton}</button>
        {alCancelar && (
          <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>
            Cancelar
          </button>
        )}
      </div>
      {error && <p className="mensaje-error" role="alert">{error}</p>}
    </form>
  );
}
