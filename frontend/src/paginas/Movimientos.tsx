// Pantalla de movimientos (RF-04, RF-05, RF-14, RF-16): registrar ingresos y egresos,
// ver el historial con filtros, corregir, anular y reactivar.
//
// El historial muestra TODO (también transferencias, cargos y ajustes, y los anulados:
// CA-13), pero aquí solo se registran y corrigen ingresos y egresos. Las transferencias
// se anulan junto con sus cargos desde su propia pantalla (RN-38).
// Las reglas (cuenta archivada, categoría desactivada o de otro tipo, monto > 0...)
// las decide la API y esta pantalla muestra su mensaje.
import { useEffect, useRef, useState, type FormEvent } from "react";

import { listarCategorias } from "../api/categorias";
import { ErrorApi } from "../api/cliente";
import { listarCuentas } from "../api/cuentas";
import {
  anularMovimiento,
  corregirMovimiento,
  listarMovimientos,
  reactivarMovimiento,
  registrarMovimiento,
} from "../api/movimientos";
import type {
  Cuenta,
  EstadoMovimiento,
  FiltroHistorial,
  Movimiento,
  RamaCategoria,
  TipoMovimiento,
} from "../api/tipos";
import { CampoDinero } from "../componentes/CampoDinero";
import { SelectorCategoria } from "../componentes/SelectorCategoria";
import { dineroParaCampo, dineroParaEnviar, esDineroValido, formatearFecha, hoy } from "../util/formato";
import { accionesPermitidas, montoConSigno, NOMBRES_TIPO_MOVIMIENTO, nombreTipo } from "../util/movimientos";

function mensajeDe(e: unknown): string {
  return e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.";
}

/** Cuentas y categorías: para los formularios y los filtros. Se piden una vez al abrir. */
interface Catalogos {
  cuentas: Cuenta[];   // también las archivadas (para filtrar el historial)
  categorias: { INGRESO: RamaCategoria[]; EGRESO: RamaCategoria[] };   // también las desactivadas
}

type Formulario = { modo: "cerrado" } | { modo: "nuevo" } | { modo: "corregir"; movimiento: Movimiento };

export function Movimientos() {
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [filtro, setFiltro] = useState<FiltroHistorial>({});
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<Formulario>({ modo: "cerrado" });
  const [ocupado, setOcupado] = useState<number | null>(null);   // movimiento con una acción en curso

  useEffect(() => {
    Promise.all([listarCuentas(true), listarCategorias("INGRESO", true), listarCategorias("EGRESO", true)])
      .then(([cuentas, ingreso, egreso]) => setCatalogos({ cuentas, categorias: { INGRESO: ingreso, EGRESO: egreso } }))
      .catch((e: unknown) => setError(mensajeDe(e)));
  }, []);

  async function cargar() {
    setCargando(true);
    try {
      setMovimientos(await listarMovimientos(filtro));
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "La fecha inicial no puede ser posterior a la fecha final."
      setMovimientos([]);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar();
  }, [filtro]);

  function abrirFormulario(nuevo: Formulario) {
    setError(null);
    setFormulario(nuevo);
  }

  async function cambiarEstado(m: Movimiento) {
    setError(null);
    setOcupado(m.id_movimiento);
    try {
      if (m.estado === "VIGENTE") await anularMovimiento(m.id_movimiento);
      else await reactivarMovimiento(m.id_movimiento);
      await cargar();
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "La cuenta está archivada: no admite movimientos."
    } finally {
      setOcupado(null);
    }
  }

  async function alGuardar() {
    setFormulario({ modo: "cerrado" });
    await cargar();
  }

  if (catalogos === null) {
    return error ? <p className="mensaje-error" role="alert">{error}</p> : <p className="cargando">Cargando…</p>;
  }

  return (
    <section>
      <div className="titulo-con-acciones">
        <h1>Movimientos</h1>
        {formulario.modo === "cerrado" && (
          <button type="button" onClick={() => abrirFormulario({ modo: "nuevo" })}>
            Registrar ingreso o egreso
          </button>
        )}
      </div>

      {formulario.modo !== "cerrado" && (
        <FormularioMovimiento
          key={formulario.modo === "corregir" ? formulario.movimiento.id_movimiento : "nuevo"}
          movimiento={formulario.modo === "corregir" ? formulario.movimiento : null}
          catalogos={catalogos}
          alGuardar={alGuardar}
          alCancelar={() => setFormulario({ modo: "cerrado" })}
        />
      )}

      <Filtros catalogos={catalogos} alAplicar={(f) => { setError(null); setFiltro(f); }} />

      {error && <p className="mensaje-error" role="alert">{error}</p>}

      {cargando ? (
        <p className="cargando">Cargando…</p>
      ) : movimientos.length === 0 ? (
        <p className="vacio">No hay movimientos con estos filtros.</p>
      ) : (
        <>
          <p className="ayuda">{movimientos.length === 1 ? "1 movimiento" : `${movimientos.length} movimientos`}</p>
          <ul className="tarjeta lista-movimientos">
            {movimientos.map((m) => (
              <FilaMovimiento
                key={m.id_movimiento}
                movimiento={m}
                ocupado={ocupado === m.id_movimiento}
                alCorregir={() => abrirFormulario({ modo: "corregir", movimiento: m })}
                alCambiarEstado={() => void cambiarEstado(m)}
              />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Una fila del historial
// ---------------------------------------------------------------------------

interface PropiedadesFila {
  movimiento: Movimiento;
  ocupado: boolean;
  alCorregir: () => void;
  alCambiarEstado: () => void;
}

function FilaMovimiento({ movimiento: m, ocupado, alCorregir, alCambiarEstado }: PropiedadesFila) {
  const acciones = accionesPermitidas(m);
  const anulado = m.estado === "ANULADO";
  const signo = montoConSigno(m);
  const claseMonto = signo.startsWith("+") ? "positivo" : signo.startsWith("−") ? "negativo" : "";
  const cuentas = m.tipo === "TRANSFERENCIA" ? `${m.nombre_cuenta} → ${m.nombre_cuenta_destino}` : m.nombre_cuenta;

  return (
    <li className={anulado ? "movimiento anulado" : "movimiento"}>
      <div className="movimiento-datos">
        <span className="movimiento-titulo">
          {m.descripcion || m.nombre_categoria || nombreTipo(m)}
          {anulado && <span className="etiqueta">Anulado</span>}
        </span>
        <span className="ayuda">
          {formatearFecha(m.fecha)} · {nombreTipo(m)}
          {m.nombre_categoria && m.descripcion ? ` · ${m.nombre_categoria}` : ""} · {cuentas}
        </span>
      </div>
      <span className={`movimiento-monto ${claseMonto}`}>{signo}</span>
      <span className="acciones">
        {acciones.corregir && (
          <button type="button" className="boton-enlace" onClick={alCorregir} disabled={ocupado}>
            Corregir
          </button>
        )}
        {acciones.anularOReactivar && (
          <button type="button" className="boton-enlace" onClick={alCambiarEstado} disabled={ocupado}>
            {anulado ? "Reactivar" : "Anular"}
          </button>
        )}
      </span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Filtros del historial
// ---------------------------------------------------------------------------

function Filtros({ catalogos, alAplicar }: { catalogos: Catalogos; alAplicar: (f: FiltroHistorial) => void }) {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [idCuenta, setIdCuenta] = useState<number | "">("");
  const [tipo, setTipo] = useState<TipoMovimiento | "">("");
  const [idCategoria, setIdCategoria] = useState<number | "">("");
  const [estado, setEstado] = useState<EstadoMovimiento | "">("");

  // Con un tipo elegido, solo sus categorías; sin tipo, todas (egresos primero).
  const ramas =
    tipo === "INGRESO" ? catalogos.categorias.INGRESO
    : tipo === "EGRESO" ? catalogos.categorias.EGRESO
    : [...catalogos.categorias.EGRESO, ...catalogos.categorias.INGRESO];

  function aplicar(evento: FormEvent) {
    evento.preventDefault();
    alAplicar({
      desde: desde || undefined,
      hasta: hasta || undefined,
      id_cuenta: idCuenta === "" ? undefined : idCuenta,
      tipo: tipo || undefined,
      id_categoria: idCategoria === "" ? undefined : idCategoria,
      estado: estado || undefined,
    });
  }

  function limpiar() {
    setDesde("");
    setHasta("");
    setIdCuenta("");
    setTipo("");
    setIdCategoria("");
    setEstado("");
    alAplicar({});
  }

  return (
    <form className="tarjeta filtros" onSubmit={aplicar}>
      <div className="campos">
        <label>
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label>
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
        <label>
          Cuenta
          <select value={idCuenta} onChange={(e) => setIdCuenta(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">Todas</option>
            {catalogos.cuentas.map((c) => (
              <option key={c.id_cuenta} value={c.id_cuenta}>
                {c.nombre}{c.activa ? "" : " (archivada)"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tipo
          <select value={tipo} onChange={(e) => { setTipo(e.target.value as TipoMovimiento | ""); setIdCategoria(""); }}>
            <option value="">Todos</option>
            {Object.entries(NOMBRES_TIPO_MOVIMIENTO).map(([valor, texto]) => (
              <option key={valor} value={valor}>{texto}</option>
            ))}
          </select>
        </label>
        <SelectorCategoria etiqueta="Categoría (incluye sus subcategorías)" ramas={ramas} valor={idCategoria}
                           alCambiar={setIdCategoria} opcionVacia="Todas" />
        <label>
          Estado
          <select value={estado} onChange={(e) => setEstado(e.target.value as EstadoMovimiento | "")}>
            <option value="">Vigentes y anulados</option>
            <option value="VIGENTE">Solo vigentes</option>
            <option value="ANULADO">Solo anulados</option>
          </select>
        </label>
      </div>
      <div className="acciones">
        <button type="submit">Filtrar</button>
        <button type="button" className="boton-secundario" onClick={limpiar}>Quitar filtros</button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Registrar o corregir un ingreso o egreso
// ---------------------------------------------------------------------------

interface PropiedadesFormulario {
  movimiento: Movimiento | null;   // null = movimiento nuevo
  catalogos: Catalogos;
  alGuardar: () => Promise<void>;
  alCancelar: () => void;
}

function FormularioMovimiento({ movimiento, catalogos, alGuardar, alCancelar }: PropiedadesFormulario) {
  const [tipo, setTipo] = useState<"INGRESO" | "EGRESO">(movimiento?.tipo === "INGRESO" ? "INGRESO" : "EGRESO");
  const [idCuenta, setIdCuenta] = useState<number | "">(movimiento?.id_cuenta ?? "");
  const [idCategoria, setIdCategoria] = useState<number | "">(movimiento?.id_categoria ?? "");
  const [monto, setMonto] = useState(movimiento ? dineroParaCampo(movimiento.monto) : "");
  const [fecha, setFecha] = useState(movimiento?.fecha ?? hoy());
  const [descripcion, setDescripcion] = useState(movimiento?.descripcion ?? "");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const formularioRef = useRef<HTMLFormElement>(null);

  // El formulario está arriba; "Corregir" puede estar muy abajo en el historial.
  useEffect(() => {
    formularioRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  // Solo lo que se puede usar: cuentas activas y categorías activas del tipo elegido.
  // Al corregir, también la cuenta y la categoría que ya tiene: la API conserva una categoría
  // desactivada si no cambia, y dice si la cuenta archivada impide corregir.
  const cuentas = catalogos.cuentas.filter((c) => c.activa || c.id_cuenta === movimiento?.id_cuenta);
  const ramas = catalogos.categorias[tipo]
    .filter((r) => r.activa || r.id_categoria === movimiento?.id_categoria)
    .map((r) => ({ ...r, subcategorias: r.subcategorias.filter((s) => s.activa || s.id_categoria === movimiento?.id_categoria) }));

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!esDineroValido(monto)) {
      setError("Escriba el monto solo con números, sin puntos de miles. Por ejemplo: 150000,50");
      return;
    }
    if (idCuenta === "" || idCategoria === "") return;   // el navegador ya lo exige (required)
    setError(null);
    setEnviando(true);   // evita el doble envío
    const datos = { id_cuenta: idCuenta, id_categoria: idCategoria, monto: dineroParaEnviar(monto), fecha, descripcion };
    try {
      if (movimiento) await corregirMovimiento(movimiento.id_movimiento, datos);
      else await registrarMovimiento(tipo, datos);
      await alGuardar();
    } catch (e) {
      setError(mensajeDe(e));
      setEnviando(false);
    }
  }

  return (
    <form ref={formularioRef} className="tarjeta formulario-ancho" onSubmit={enviar}>
      <h2>{movimiento ? `Corregir ${tipo === "INGRESO" ? "ingreso" : "egreso"}` : "Registrar movimiento"}</h2>

      {movimiento === null && (
        <div className="pestanas" role="tablist">
          {(["EGRESO", "INGRESO"] as const).map((t) => (
            <button key={t} type="button" role="tab" aria-selected={tipo === t}
                    className={tipo === t ? "pestana activa" : "pestana"}
                    onClick={() => { setTipo(t); setIdCategoria(""); }}>
              {t === "EGRESO" ? "Egreso" : "Ingreso"}
            </button>
          ))}
        </div>
      )}

      <div className="campos">
        <label>
          Cuenta
          <select value={idCuenta} required onChange={(e) => setIdCuenta(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">Elija una cuenta</option>
            {cuentas.map((c) => (
              <option key={c.id_cuenta} value={c.id_cuenta}>
                {c.nombre}{c.activa ? "" : " (archivada)"}
              </option>
            ))}
          </select>
        </label>
        <SelectorCategoria etiqueta="Categoría" ramas={ramas} valor={idCategoria} alCambiar={setIdCategoria} />
        <CampoDinero etiqueta="Monto" valor={monto} alCambiar={setMonto} />
        <label>
          Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </label>
        <label className="campo-ancho">
          Descripción (opcional)
          <input type="text" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </label>
      </div>
      {movimiento && <p className="ayuda">El tipo no se puede cambiar. Si se equivocó de tipo, anule este y registre otro.</p>}
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
        <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
