// Pantalla de cuentas (RF-02, RF-11): ver, crear, editar, archivar y reactivar.
//
// Las reglas las decide la API y esta pantalla muestra su mensaje. Por ejemplo:
//   * Solo se archiva una cuenta con saldo 0 (RN-12, CA-15).
//   * El saldo inicial no cambia si la cuenta ya tiene movimientos (RN-13).
//   * Un saldo negativo se avisa, pero no se bloquea (RN-14).
// Después de cada acción se vuelve a pedir la lista: el saldo siempre lo calcula la API.
import { useEffect, useState, type FormEvent } from "react";

import { ErrorApi } from "../api/cliente";
import { archivarCuenta, crearCuenta, editarCuenta, listarCuentas, reactivarCuenta } from "../api/cuentas";
import type { Cuenta, TipoCuenta } from "../api/tipos";
import { CampoDinero } from "../componentes/CampoDinero";
import { dineroParaCampo, dineroParaEnviar, esDineroValido, formatearDinero } from "../util/formato";

/** Cómo se muestra cada tipo de cuenta. */
export const NOMBRES_TIPO: Record<TipoCuenta, string> = {
  EFECTIVO: "Efectivo",
  AHORROS: "Ahorros",
  CORRIENTE: "Corriente",
  BILLETERA_DIGITAL: "Billetera digital",
  OTRA: "Otra",
};

function mensajeDe(e: unknown): string {
  return e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.";
}

/** Qué muestra el formulario: nada, una cuenta nueva o la edición de una cuenta. */
type Formulario = { modo: "cerrado" } | { modo: "nueva" } | { modo: "editar"; cuenta: Cuenta };

export function Cuentas() {
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [verArchivadas, setVerArchivadas] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<Formulario>({ modo: "cerrado" });
  const [ocupada, setOcupada] = useState<number | null>(null);   // cuenta con una acción en curso

  async function cargar() {
    try {
      setCuentas(await listarCuentas(verArchivadas));
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar();
  }, [verArchivadas]);

  function abrirFormulario(nuevo: Formulario) {
    setError(null);
    setFormulario(nuevo);
  }

  async function cambiarEstado(cuenta: Cuenta) {
    setError(null);
    setOcupada(cuenta.id_cuenta);
    try {
      if (cuenta.activa) await archivarCuenta(cuenta.id_cuenta);
      else await reactivarCuenta(cuenta.id_cuenta);
      await cargar();
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "La cuenta tiene un saldo de ... Para archivarla..."
    } finally {
      setOcupada(null);
    }
  }

  async function alGuardar() {
    setFormulario({ modo: "cerrado" });
    await cargar();
  }

  return (
    <section>
      <div className="titulo-con-acciones">
        <h1>Cuentas</h1>
        {formulario.modo === "cerrado" && (
          <button type="button" onClick={() => abrirFormulario({ modo: "nueva" })}>
            Nueva cuenta
          </button>
        )}
      </div>

      {formulario.modo !== "cerrado" && (
        <FormularioCuenta
          key={formulario.modo === "editar" ? formulario.cuenta.id_cuenta : "nueva"}
          cuenta={formulario.modo === "editar" ? formulario.cuenta : null}
          alGuardar={alGuardar}
          alCancelar={() => setFormulario({ modo: "cerrado" })}
        />
      )}

      <label className="casilla">
        <input type="checkbox" checked={verArchivadas} onChange={(e) => setVerArchivadas(e.target.checked)} />
        Mostrar también las cuentas archivadas
      </label>

      {error && <p className="mensaje-error" role="alert">{error}</p>}

      {cargando ? (
        <p className="cargando">Cargando…</p>
      ) : cuentas.length === 0 ? (
        <p className="vacio">Todavía no tiene cuentas. Cree la primera con "Nueva cuenta".</p>
      ) : (
        <div className="lista-tarjetas">
          {cuentas.map((c) => (
            <TarjetaCuenta
              key={c.id_cuenta}
              cuenta={c}
              ocupada={ocupada === c.id_cuenta}
              alEditar={() => abrirFormulario({ modo: "editar", cuenta: c })}
              alCambiarEstado={() => void cambiarEstado(c)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

interface PropiedadesTarjeta {
  cuenta: Cuenta;
  ocupada: boolean;
  alEditar: () => void;
  alCambiarEstado: () => void;
}

function TarjetaCuenta({ cuenta, ocupada, alEditar, alCambiarEstado }: PropiedadesTarjeta) {
  const clases = ["tarjeta", "cuenta", cuenta.activa ? "" : "archivada"];
  return (
    <article className={clases.join(" ").trim()}>
      <div className="cuenta-cabecera">
        <h3>{cuenta.nombre}</h3>
        <span className="etiqueta">{cuenta.activa ? NOMBRES_TIPO[cuenta.tipo] : "Archivada"}</span>
      </div>
      <span className={cuenta.saldo_negativo ? "cifra-valor negativo" : "cifra-valor"}>
        {formatearDinero(cuenta.saldo)}
      </span>
      {cuenta.saldo_negativo && (
        <p className="aviso" role="status">El saldo es negativo. Se permite, pero revise sus movimientos.</p>
      )}
      <span className="ayuda">Saldo inicial: {formatearDinero(cuenta.saldo_inicial)}</span>
      <div className="acciones">
        {cuenta.activa && (
          <button type="button" className="boton-secundario" onClick={alEditar} disabled={ocupada}>
            Editar
          </button>
        )}
        <button type="button" className="boton-secundario" onClick={alCambiarEstado} disabled={ocupada}>
          {ocupada ? "Un momento…" : cuenta.activa ? "Archivar" : "Reactivar"}
        </button>
      </div>
    </article>
  );
}

interface PropiedadesFormulario {
  cuenta: Cuenta | null;   // null = cuenta nueva
  alGuardar: () => Promise<void>;
  alCancelar: () => void;
}

function FormularioCuenta({ cuenta, alGuardar, alCancelar }: PropiedadesFormulario) {
  const [nombre, setNombre] = useState(cuenta?.nombre ?? "");
  const [tipo, setTipo] = useState<TipoCuenta>(cuenta?.tipo ?? "AHORROS");
  const [saldoInicial, setSaldoInicial] = useState(cuenta ? dineroParaCampo(cuenta.saldo_inicial) : "0");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!esDineroValido(saldoInicial)) {
      // Ayuda con lo evidente; las demás reglas del saldo (máximo, RN-13) las revisa la API.
      setError("Escriba el saldo inicial solo con números, sin puntos de miles. Por ejemplo: 150000,50");
      return;
    }
    setError(null);
    setEnviando(true);   // evita el doble envío
    const datos = { nombre, tipo, saldo_inicial: dineroParaEnviar(saldoInicial) };
    try {
      if (cuenta) await editarCuenta(cuenta.id_cuenta, datos);
      else await crearCuenta(datos);
      await alGuardar();
    } catch (e) {
      setError(mensajeDe(e));
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta formulario-ancho" onSubmit={enviar}>
      <h2>{cuenta ? `Editar "${cuenta.nombre}"` : "Nueva cuenta"}</h2>
      <div className="campos">
        <label>
          Nombre
          <input type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        </label>
        <label>
          Tipo
          <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoCuenta)}>
            {Object.entries(NOMBRES_TIPO).map(([valor, texto]) => (
              <option key={valor} value={valor}>{texto}</option>
            ))}
          </select>
        </label>
        <CampoDinero etiqueta="Saldo inicial" valor={saldoInicial} alCambiar={setSaldoInicial}
                     ayuda={cuenta ? "solo cambia si la cuenta no tiene movimientos" : undefined} />
      </div>
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
