// Pantalla de ajustes de saldo (RF-17).
//
// El saldo no se escribe encima (no se guarda: se calcula, D-11). El usuario dice cuál
// es el SALDO REAL que ve en su banco y la API calcula la diferencia con el saldo
// calculado. Si hay diferencia, la registra como un ajuste visible, con motivo y
// anulable (D-12, RN-50 a RN-55). Esta pantalla no calcula la diferencia: muestra la
// que respondió la API.
//
// Abajo, los ajustes registrados: se corrigen la fecha y el motivo (el monto salió de
// un cálculo, no se corrige) y se anulan o reactivan como cualquier movimiento (RN-54).
import { useEffect, useState, type FormEvent } from "react";

import { ajustarSaldo, corregirAjuste, listarAjustes } from "../api/ajustes";
import { ErrorApi } from "../api/cliente";
import { listarCuentas } from "../api/cuentas";
import { anularMovimiento, reactivarMovimiento } from "../api/movimientos";
import type { Cuenta, Movimiento, ResultadoAjuste } from "../api/tipos";
import { CampoDinero } from "../componentes/CampoDinero";
import { dineroParaEnviar, esDineroValido, esNegativo, formatearDinero, formatearFecha, hoy } from "../util/formato";
import { montoConSigno } from "../util/movimientos";

function mensajeDe(e: unknown): string {
  return e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.";
}

export function Ajustes() {
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [ajustes, setAjustes] = useState<Movimiento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [corrigiendo, setCorrigiendo] = useState<number | null>(null);   // ajuste con el formulario abierto
  const [ocupado, setOcupado] = useState<number | null>(null);

  /** Cuentas (con su saldo calculado) y ajustes: después de cada cambio se piden de nuevo. */
  async function cargar() {
    try {
      const [c, a] = await Promise.all([listarCuentas(), listarAjustes()]);
      setCuentas(c);
      setAjustes(a);
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar();
  }, []);

  async function cambiarEstado(a: Movimiento) {
    setError(null);
    setOcupado(a.id_movimiento);
    try {
      if (a.estado === "VIGENTE") await anularMovimiento(a.id_movimiento);
      else await reactivarMovimiento(a.id_movimiento);
      await cargar();
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setOcupado(null);
    }
  }

  if (cargando) return <p className="cargando">Cargando…</p>;

  return (
    <section>
      <h1>Ajustes de saldo</h1>
      <p className="nota">
        Si el saldo de una cuenta no coincide con el de su banco, escriba el saldo real. Se registra la
        diferencia como un ajuste: no cuenta como ingreso ni como gasto, y se puede anular.
      </p>

      <FormularioAjuste cuentas={cuentas} alAjustar={cargar} />

      <h2>Ajustes registrados</h2>
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      {ajustes.length === 0 ? (
        <p className="vacio">Todavía no hay ajustes.</p>
      ) : (
        <ul className="tarjeta lista-movimientos">
          {ajustes.map((a) =>
            corrigiendo === a.id_movimiento ? (
              <li key={a.id_movimiento} className="movimiento-edicion">
                <FormularioCorregir ajuste={a} alCancelar={() => setCorrigiendo(null)}
                                    alGuardar={async () => { setCorrigiendo(null); await cargar(); }} />
              </li>
            ) : (
              <FilaAjuste key={a.id_movimiento} ajuste={a} ocupado={ocupado === a.id_movimiento}
                          alCorregir={() => { setError(null); setCorrigiendo(a.id_movimiento); }}
                          alCambiarEstado={() => void cambiarEstado(a)} />
            ),
          )}
        </ul>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Ajustar el saldo de una cuenta
// ---------------------------------------------------------------------------

function FormularioAjuste({ cuentas, alAjustar }: { cuentas: Cuenta[]; alAjustar: () => Promise<void> }) {
  const [idCuenta, setIdCuenta] = useState<number | "">("");
  const [saldoReal, setSaldoReal] = useState("");
  const [motivo, setMotivo] = useState("");
  const [fecha, setFecha] = useState(hoy());
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoAjuste | null>(null);
  const [enviando, setEnviando] = useState(false);

  const cuenta = cuentas.find((c) => c.id_cuenta === idCuenta);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!esDineroValido(saldoReal, true)) {
      setError("Escriba el saldo real solo con números, sin puntos de miles. Si es negativo, con - al inicio.");
      return;
    }
    if (idCuenta === "") return;
    setError(null);
    setResultado(null);
    setEnviando(true);
    try {
      setResultado(await ajustarSaldo(idCuenta, dineroParaEnviar(saldoReal), motivo, fecha));
      setSaldoReal("");
      setMotivo("");
      await alAjustar();
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "El motivo del ajuste es obligatorio."
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta formulario-ancho" onSubmit={enviar}>
      <h2>Ajustar el saldo de una cuenta</h2>
      <div className="campos">
        <label>
          Cuenta
          <select value={idCuenta} required
                  onChange={(e) => { setIdCuenta(e.target.value === "" ? "" : Number(e.target.value)); setResultado(null); }}>
            <option value="">Elija una cuenta</option>
            {cuentas.map((c) => (
              <option key={c.id_cuenta} value={c.id_cuenta}>{c.nombre}</option>
            ))}
          </select>
          {cuenta && <span className="ayuda">Saldo en FINANCIA+: {formatearDinero(cuenta.saldo)}</span>}
        </label>
        <CampoDinero etiqueta="Saldo real (el que ve en su banco)" valor={saldoReal} alCambiar={setSaldoReal}
                     permitirNegativo ayuda="si es negativo, escriba - al inicio" />
        <label>
          Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </label>
        <label className="campo-ancho">
          Motivo
          <input type="text" value={motivo} onChange={(e) => setMotivo(e.target.value)} required
                 placeholder="Por ejemplo: compras que no registré" />
        </label>
      </div>
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      {resultado && <Resultado datos={resultado} />}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Ajustando…" : "Ajustar saldo"}</button>
      </div>
    </form>
  );
}

/** Lo que respondió la API: si hubo ajuste, de qué tipo y por cuánto; si no, que ya coincidía (RN-51). */
function Resultado({ datos }: { datos: ResultadoAjuste }) {
  const { cuenta, ajuste } = datos;
  if (ajuste === null) {
    return (
      <p className="aviso" role="status">
        El saldo de {cuenta.nombre} ya era {formatearDinero(cuenta.saldo)}: no hizo falta ningún ajuste.
      </p>
    );
  }
  const aumento = ajuste.tipo === "AJUSTE_AUMENTO";
  return (
    <p className="aviso exito" role="status">
      {cuenta.nombre}: el saldo pasó de {formatearDinero(datos.saldo_anterior)} a{" "}
      <strong className={esNegativo(cuenta.saldo) ? "negativo" : ""}>{formatearDinero(cuenta.saldo)}</strong>. Se
      registró un ajuste de {aumento ? "aumento" : "disminución"} por {formatearDinero(ajuste.monto)}.
    </p>
  );
}

// ---------------------------------------------------------------------------
// Un ajuste registrado
// ---------------------------------------------------------------------------

interface PropiedadesFila {
  ajuste: Movimiento;
  ocupado: boolean;
  alCorregir: () => void;
  alCambiarEstado: () => void;
}

function FilaAjuste({ ajuste: a, ocupado, alCorregir, alCambiarEstado }: PropiedadesFila) {
  const anulado = a.estado === "ANULADO";
  const signo = montoConSigno(a);
  return (
    <li className={anulado ? "movimiento anulado" : "movimiento"}>
      <div className="movimiento-datos">
        <span className="movimiento-titulo">
          {a.descripcion}
          {anulado && <span className="etiqueta">Anulado</span>}
        </span>
        <span className="ayuda">
          {formatearFecha(a.fecha)} · {a.tipo === "AJUSTE_AUMENTO" ? "Aumento" : "Disminución"} · {a.nombre_cuenta}
        </span>
      </div>
      <span className={`movimiento-monto ${signo.startsWith("+") ? "positivo" : "negativo"}`}>{signo}</span>
      <span className="acciones">
        {!anulado && (
          <button type="button" className="boton-enlace" onClick={alCorregir} disabled={ocupado}>Corregir</button>
        )}
        <button type="button" className="boton-enlace" onClick={alCambiarEstado} disabled={ocupado}>
          {anulado ? "Reactivar" : "Anular"}
        </button>
      </span>
    </li>
  );
}

interface PropiedadesCorregir {
  ajuste: Movimiento;
  alGuardar: () => Promise<void>;
  alCancelar: () => void;
}

/** Solo fecha y motivo. Si el monto quedó mal, se anula el ajuste y se hace otro con el saldo real correcto. */
function FormularioCorregir({ ajuste, alGuardar, alCancelar }: PropiedadesCorregir) {
  const [fecha, setFecha] = useState(ajuste.fecha);
  const [motivo, setMotivo] = useState(ajuste.descripcion ?? "");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await corregirAjuste(ajuste.id_movimiento, fecha, motivo);
      await alGuardar();
    } catch (e) {
      setError(mensajeDe(e));
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar}>
      <div className="campos">
        <label>
          Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </label>
        <label>
          Motivo
          <input type="text" value={motivo} onChange={(e) => setMotivo(e.target.value)} required />
        </label>
      </div>
      <p className="ayuda">
        El monto ({formatearDinero(ajuste.monto)}) no se corrige: salió de un cálculo. Si quedó mal, anule este
        ajuste y haga otro con el saldo real correcto.
      </p>
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
        <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>Cancelar</button>
      </div>
    </form>
  );
}
