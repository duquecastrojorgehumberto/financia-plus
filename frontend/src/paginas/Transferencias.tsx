// Pantalla de transferencias entre cuentas propias, con sus cargos (RF-06, RF-07).
//
// Una transferencia es UNA fila (origen → destino, sin categoría) y cada cargo es un
// EGRESO normal de la cuenta de origen que apunta a ella (RN-33 a RN-35). El usuario
// escribe el valor real de cada cargo; nada se calcula aquí (RN-36).
//
// La lista sale del historial; al abrir una transferencia se piden sus cargos.
// Lo que decide la API y esta pantalla solo muestra:
//   * Transferencia y cargos se guardan juntos o no se guarda nada (RN-37, CA-03).
//   * Anular la transferencia anula sus cargos (RN-38, CA-04); reactivarla NO los
//     reactiva: cada cargo vuelve aparte.
//   * La cuenta de origen no cambia si hay cargos (RN-72); las dos cuentas deben estar activas.
import { useEffect, useRef, useState, type FormEvent } from "react";

import { listarCategorias } from "../api/categorias";
import { ErrorApi } from "../api/cliente";
import { listarCuentas } from "../api/cuentas";
import { anularMovimiento, reactivarMovimiento } from "../api/movimientos";
import type { Cuenta, DatosCargo, Movimiento, RamaCategoria, Transferencia } from "../api/tipos";
import {
  agregarCargo,
  anularTransferencia,
  corregirCargo,
  corregirTransferencia,
  listarTransferencias,
  obtenerTransferencia,
  reactivarTransferencia,
  registrarTransferencia,
} from "../api/transferencias";
import { CampoDinero } from "../componentes/CampoDinero";
import { SelectorCategoria } from "../componentes/SelectorCategoria";
import { ramasUtilizables } from "../util/categorias";
import { dineroParaCampo, dineroParaEnviar, esDineroValido, formatearDinero, formatearFecha, hoy } from "../util/formato";

function mensajeDe(e: unknown): string {
  return e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.";
}

const MENSAJE_MONTO = "Escriba los montos solo con números, sin puntos de miles. Por ejemplo: 150000,50";

/** Cuentas (también archivadas, para mostrar nombres) y categorías de egreso (para los cargos). */
interface Catalogos {
  cuentas: Cuenta[];
  categoriasEgreso: RamaCategoria[];
}

export function Transferencias() {
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [transferencias, setTransferencias] = useState<Movimiento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nueva, setNueva] = useState(false);
  const [abierta, setAbierta] = useState<number | null>(null);   // la que muestra su detalle

  useEffect(() => {
    Promise.all([listarCuentas(true), listarCategorias("EGRESO", true)])
      .then(([cuentas, categoriasEgreso]) => setCatalogos({ cuentas, categoriasEgreso }))
      .catch((e: unknown) => setError(mensajeDe(e)));
    void cargar();
  }, []);

  async function cargar() {
    try {
      setTransferencias(await listarTransferencias());
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setCargando(false);
    }
  }

  async function alRegistrar(t: Transferencia) {
    setNueva(false);
    await cargar();
    setAbierta(t.id_movimiento);   // se abre la recién creada para ver sus cargos
  }

  if (catalogos === null) {
    return error ? <p className="mensaje-error" role="alert">{error}</p> : <p className="cargando">Cargando…</p>;
  }

  return (
    <section>
      <div className="titulo-con-acciones">
        <h1>Transferencias</h1>
        {!nueva && (
          <button type="button" onClick={() => { setError(null); setNueva(true); }}>
            Nueva transferencia
          </button>
        )}
      </div>

      {nueva && (
        <FormularioTransferencia transferencia={null} catalogos={catalogos}
                                 alGuardar={alRegistrar} alCancelar={() => setNueva(false)} />
      )}

      {error && <p className="mensaje-error" role="alert">{error}</p>}

      {cargando ? (
        <p className="cargando">Cargando…</p>
      ) : transferencias.length === 0 ? (
        <p className="vacio">Todavía no hay transferencias.</p>
      ) : (
        <ul className="lista-transferencias">
          {transferencias.map((t) => (
            <li key={t.id_movimiento} className={t.estado === "ANULADO" ? "tarjeta transferencia anulada" : "tarjeta transferencia"}>
              <button type="button" className="transferencia-resumen" aria-expanded={abierta === t.id_movimiento}
                      onClick={() => setAbierta(abierta === t.id_movimiento ? null : t.id_movimiento)}>
                <span className="movimiento-datos">
                  <span className="movimiento-titulo">
                    {t.descripcion || "Transferencia"}
                    {t.estado === "ANULADO" && <span className="etiqueta">Anulada</span>}
                  </span>
                  <span className="ayuda">
                    {formatearFecha(t.fecha)} · {t.nombre_cuenta} → {t.nombre_cuenta_destino}
                  </span>
                </span>
                <span className="movimiento-monto">{formatearDinero(t.monto)}</span>
                <span className="flecha" aria-hidden="true">{abierta === t.id_movimiento ? "▲" : "▼"}</span>
              </button>
              {abierta === t.id_movimiento && (
                <DetalleTransferencia idTransferencia={t.id_movimiento} catalogos={catalogos} alCambiar={cargar} />
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Detalle: los cargos y las acciones de una transferencia
// ---------------------------------------------------------------------------

/** Qué formulario está abierto dentro del detalle. */
type Edicion =
  | { modo: "ninguna" }
  | { modo: "transferencia" }
  | { modo: "nuevo-cargo" }
  | { modo: "cargo"; cargo: Movimiento };

interface PropiedadesDetalle {
  idTransferencia: number;
  catalogos: Catalogos;
  alCambiar: () => Promise<void>;   // para que la lista refleje el cambio
}

function DetalleTransferencia({ idTransferencia, catalogos, alCambiar }: PropiedadesDetalle) {
  const [t, setT] = useState<Transferencia | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [edicion, setEdicion] = useState<Edicion>({ modo: "ninguna" });
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    obtenerTransferencia(idTransferencia).then(setT).catch((e: unknown) => setError(mensajeDe(e)));
  }, [idTransferencia]);

  /** Después de un cambio: la API devuelve la transferencia actualizada; la lista también se recarga. */
  async function aplicar(actualizada: Transferencia, mensaje?: string) {
    setT(actualizada);
    setEdicion({ modo: "ninguna" });
    setAviso(mensaje ?? null);
    await alCambiar();
  }

  /** Para los botones de una sola acción (anular, reactivar). */
  async function accion(hacer: () => Promise<Transferencia>, mensaje?: (t: Transferencia) => string | undefined) {
    setError(null);
    setAviso(null);
    setOcupado(true);
    try {
      const actualizada = await hacer();
      await aplicar(actualizada, mensaje?.(actualizada));
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "Una cuenta de la transferencia está archivada..."
    } finally {
      setOcupado(false);
    }
  }

  if (t === null) {
    return error ? <p className="mensaje-error" role="alert">{error}</p> : <p className="cargando">Cargando…</p>;
  }

  const vigente = t.estado === "VIGENTE";
  const cargosVigentes = t.cargos.filter((c) => c.estado === "VIGENTE").length;

  function anular() {
    if (t === null) return;
    if (cargosVigentes > 0 && !window.confirm(
      `También se anularán sus ${cargosVigentes} cargos vigentes. Si después la reactiva, los cargos ` +
        "no vuelven solos: se reactivan uno por uno. ¿Continuar?")) {
      return;
    }
    void accion(() => anularTransferencia(t.id_movimiento));
  }

  function reactivar() {
    if (t === null) return;
    void accion(() => reactivarTransferencia(t.id_movimiento), (r) =>
      r.cargos.some((c) => c.estado === "ANULADO")
        ? "La transferencia volvió a estar vigente. Sus cargos siguen anulados: reactive los que correspondan."
        : undefined);
  }

  /** Un cargo se anula o reactiva solo, con las rutas de movimientos (RN-38). */
  function cambiarEstadoCargo(cargo: Movimiento) {
    if (t === null) return;
    void accion(async () => {
      if (cargo.estado === "VIGENTE") await anularMovimiento(cargo.id_movimiento);
      else await reactivarMovimiento(cargo.id_movimiento);
      return obtenerTransferencia(t.id_movimiento);
    });
  }

  return (
    <div className="detalle-transferencia">
      {edicion.modo === "transferencia" ? (
        <FormularioTransferencia transferencia={t} catalogos={catalogos}
                                 alGuardar={(r) => aplicar(r)} alCancelar={() => setEdicion({ modo: "ninguna" })} />
      ) : (
        <div className="acciones">
          {vigente && (
            <>
              <button type="button" className="boton-secundario" disabled={ocupado}
                      onClick={() => setEdicion({ modo: "transferencia" })}>
                Corregir transferencia
              </button>
              <button type="button" className="boton-secundario" disabled={ocupado} onClick={anular}>
                Anular
              </button>
            </>
          )}
          {!vigente && (
            <button type="button" className="boton-secundario" disabled={ocupado} onClick={reactivar}>
              Reactivar
            </button>
          )}
        </div>
      )}

      {error && <p className="mensaje-error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}

      <h3>Cargos</h3>
      {t.cargos.length === 0 ? (
        <p className="vacio">Sin cargos.</p>
      ) : (
        <ul className="lista-cargos">
          {t.cargos.map((c) =>
            edicion.modo === "cargo" && edicion.cargo.id_movimiento === c.id_movimiento ? (
              <li key={c.id_movimiento}>
                <FormularioCargo idTransferencia={t.id_movimiento} cargo={c} catalogos={catalogos}
                                 alGuardar={(r) => aplicar(r)} alCancelar={() => setEdicion({ modo: "ninguna" })} />
              </li>
            ) : (
              <li key={c.id_movimiento} className={c.estado === "ANULADO" ? "cargo anulado" : "cargo"}>
                <span className="movimiento-datos">
                  <span className="movimiento-titulo">
                    {c.descripcion || c.nombre_categoria}
                    {c.estado === "ANULADO" && <span className="etiqueta">Anulado</span>}
                  </span>
                  <span className="ayuda">{c.nombre_categoria} · sale de {c.nombre_cuenta}</span>
                </span>
                <span className="movimiento-monto negativo">{formatearDinero(`-${c.monto}`)}</span>
                <span className="acciones">
                  {vigente && c.estado === "VIGENTE" && (
                    <button type="button" className="boton-enlace" disabled={ocupado}
                            onClick={() => setEdicion({ modo: "cargo", cargo: c })}>
                      Corregir
                    </button>
                  )}
                  <button type="button" className="boton-enlace" disabled={ocupado} onClick={() => cambiarEstadoCargo(c)}>
                    {c.estado === "VIGENTE" ? "Anular" : "Reactivar"}
                  </button>
                </span>
              </li>
            ),
          )}
        </ul>
      )}
      {t.cargos.length > 0 && <p className="ayuda">Total de cargos vigentes: {formatearDinero(t.total_cargos)}</p>}

      {vigente &&
        (edicion.modo === "nuevo-cargo" ? (
          <FormularioCargo idTransferencia={t.id_movimiento} cargo={null} catalogos={catalogos}
                           alGuardar={(r) => aplicar(r)} alCancelar={() => setEdicion({ modo: "ninguna" })} />
        ) : (
          <button type="button" className="boton-enlace" disabled={ocupado}
                  onClick={() => setEdicion({ modo: "nuevo-cargo" })}>
            + Agregar cargo
          </button>
        ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Registrar o corregir una transferencia
// ---------------------------------------------------------------------------

/** Un cargo mientras se escribe en el formulario de una transferencia nueva. */
interface CargoEnFormulario {
  clave: number;   // solo para React (key): identifica la fila aunque se borren otras
  monto: string;
  idCategoria: number | "";
  descripcion: string;
}

interface PropiedadesFormularioTransferencia {
  transferencia: Transferencia | null;   // null = nueva
  catalogos: Catalogos;
  alGuardar: (t: Transferencia) => Promise<void>;
  alCancelar: () => void;
}

function FormularioTransferencia({ transferencia: t, catalogos, alGuardar, alCancelar }: PropiedadesFormularioTransferencia) {
  const [origen, setOrigen] = useState<number | "">(t?.id_cuenta ?? "");
  const [destino, setDestino] = useState<number | "">(t?.id_cuenta_destino ?? "");
  const [monto, setMonto] = useState(t ? dineroParaCampo(t.monto) : "");
  const [fecha, setFecha] = useState(t?.fecha ?? hoy());
  const [descripcion, setDescripcion] = useState(t?.descripcion ?? "");
  const [cargos, setCargos] = useState<CargoEnFormulario[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const siguienteClave = useRef(1);

  const cuentas = catalogos.cuentas.filter((c) => c.activa || c.id_cuenta === t?.id_cuenta || c.id_cuenta === t?.id_cuenta_destino);
  const ramas = ramasUtilizables(catalogos.categoriasEgreso);
  const origenFijo = t !== null && t.cargos.length > 0;   // RN-72

  function cambiarCargo(clave: number, cambios: Partial<CargoEnFormulario>) {
    setCargos(cargos.map((c) => (c.clave === clave ? { ...c, ...cambios } : c)));
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!esDineroValido(monto) || cargos.some((c) => !esDineroValido(c.monto))) {
      setError(MENSAJE_MONTO);
      return;
    }
    if (origen === "" || destino === "") return;   // el navegador ya lo exige (required)
    setError(null);
    setEnviando(true);   // evita el doble envío
    const datos = { id_cuenta_origen: origen, id_cuenta_destino: destino, monto: dineroParaEnviar(monto), fecha, descripcion };
    try {
      const guardada = t
        ? await corregirTransferencia(t.id_movimiento, datos)
        : await registrarTransferencia(datos, cargos.map((c): DatosCargo => ({
            monto: dineroParaEnviar(c.monto),
            id_categoria: Number(c.idCategoria),
            descripcion: c.descripcion,
          })));
      await alGuardar(guardada);
    } catch (e) {
      setError(mensajeDe(e));   // si algo falla no se guardó nada: ni la transferencia ni los cargos (CA-03)
      setEnviando(false);
    }
  }

  const opcionesCuenta = cuentas.map((c) => (
    <option key={c.id_cuenta} value={c.id_cuenta}>{c.nombre}{c.activa ? "" : " (archivada)"}</option>
  ));

  return (
    <form className="tarjeta formulario-ancho" onSubmit={enviar}>
      <h2>{t ? "Corregir transferencia" : "Nueva transferencia"}</h2>
      <div className="campos">
        <label>
          Cuenta de origen
          <select value={origen} required disabled={origenFijo}
                  onChange={(e) => setOrigen(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">Elija una cuenta</option>
            {opcionesCuenta}
          </select>
          {origenFijo && <span className="ayuda">No se cambia porque la transferencia tiene cargos.</span>}
        </label>
        <label>
          Cuenta de destino
          <select value={destino} required onChange={(e) => setDestino(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">Elija una cuenta</option>
            {opcionesCuenta}
          </select>
        </label>
        <CampoDinero etiqueta="Monto que se transfiere" valor={monto} alCambiar={setMonto} />
        <label>
          Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </label>
        <label className="campo-ancho">
          Descripción (opcional)
          <input type="text" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </label>
      </div>

      {t === null && (
        <fieldset className="cargos-nuevos">
          <legend>Cargos (opcional)</legend>
          <p className="ayuda">
            Lo que cobró el banco por la transferencia, por ejemplo el 4×1.000. Escriba el valor real: el
            sistema no lo calcula. Salen de la cuenta de origen, con la misma fecha.
          </p>
          {cargos.map((c) => (
            <div key={c.clave} className="campos fila-cargo">
              <CampoDinero etiqueta="Valor del cargo" valor={c.monto} alCambiar={(v) => cambiarCargo(c.clave, { monto: v })} />
              <SelectorCategoria etiqueta="Categoría" ramas={ramas} valor={c.idCategoria}
                                 alCambiar={(v) => cambiarCargo(c.clave, { idCategoria: v })} />
              <label>
                Descripción (opcional)
                <input type="text" value={c.descripcion} onChange={(e) => cambiarCargo(c.clave, { descripcion: e.target.value })} />
              </label>
              <button type="button" className="boton-enlace quitar" onClick={() => setCargos(cargos.filter((x) => x.clave !== c.clave))}>
                Quitar
              </button>
            </div>
          ))}
          <button type="button" className="boton-enlace"
                  onClick={() => setCargos([...cargos, { clave: siguienteClave.current++, monto: "", idCategoria: "", descripcion: "" }])}>
            + Agregar cargo
          </button>
        </fieldset>
      )}

      {error && <p className="mensaje-error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
        <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>Cancelar</button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Agregar o corregir un cargo de una transferencia existente
// ---------------------------------------------------------------------------

interface PropiedadesFormularioCargo {
  idTransferencia: number;
  cargo: Movimiento | null;   // null = cargo nuevo
  catalogos: Catalogos;
  alGuardar: (t: Transferencia) => Promise<void>;
  alCancelar: () => void;
}

function FormularioCargo({ idTransferencia, cargo, catalogos, alGuardar, alCancelar }: PropiedadesFormularioCargo) {
  const [monto, setMonto] = useState(cargo ? dineroParaCampo(cargo.monto) : "");
  const [idCategoria, setIdCategoria] = useState<number | "">(cargo?.id_categoria ?? "");
  const [descripcion, setDescripcion] = useState(cargo?.descripcion ?? "");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!esDineroValido(monto)) {
      setError(MENSAJE_MONTO);
      return;
    }
    if (idCategoria === "") return;
    setError(null);
    setEnviando(true);
    const datos = { monto: dineroParaEnviar(monto), id_categoria: idCategoria, descripcion };
    try {
      await alGuardar(cargo
        ? await corregirCargo(idTransferencia, cargo.id_movimiento, datos)
        : await agregarCargo(idTransferencia, datos));
    } catch (e) {
      setError(mensajeDe(e));
      setEnviando(false);
    }
  }

  return (
    <form className="formulario-cargo" onSubmit={enviar}>
      <div className="campos">
        <CampoDinero etiqueta={cargo ? "Valor del cargo" : "Valor del cargo nuevo"} valor={monto} alCambiar={setMonto} />
        <SelectorCategoria etiqueta="Categoría" ramas={ramasUtilizables(catalogos.categoriasEgreso, cargo?.id_categoria)}
                           valor={idCategoria} alCambiar={setIdCategoria} />
        <label>
          Descripción (opcional)
          <input type="text" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </label>
      </div>
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar cargo"}</button>
        <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>Cancelar</button>
      </div>
    </form>
  );
}
