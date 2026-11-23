// Pantalla de bolsillos y metas (RF-08, RF-09, RF-10, RF-12).
//
// Un bolsillo es una reserva virtual: no está en ninguna cuenta (D-10). El usuario
// escribe directamente cuánto tiene apartado (RN-42); cada cambio queda en el
// historial (RN-44) y no es un ingreso ni un gasto (RN-47). Lo reservado se resta
// del "disponible" en el Resumen.
//
// Es una META si tiene monto objetivo (D-08). El progreso lo calcula la API (RN-48)
// y aquí solo se dibuja la barra.
import { useEffect, useState, type FormEvent } from "react";

import {
  archivarBolsillo,
  cambiarValor,
  crearBolsillo,
  editarBolsillo,
  historialBolsillo,
  listarBolsillos,
  reactivarBolsillo,
} from "../api/bolsillos";
import { ErrorApi } from "../api/cliente";
import type { Bolsillo, ValorBolsillo } from "../api/tipos";
import { CampoDinero } from "../componentes/CampoDinero";
import { coloresPorId } from "../graficos/colores";
import { prepararMetas } from "../graficos/datos";
import { ProgresoMetas } from "../graficos/ProgresoMetas";
import {
  dineroParaCampo,
  dineroParaEnviar,
  esDineroValido,
  formatearDinero,
  formatearFecha,
  formatearFechaHora,
  formatearPorcentaje,
} from "../util/formato";

function mensajeDe(e: unknown): string {
  return e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.";
}

const MENSAJE_MONTO = "Escriba los montos solo con números, sin puntos de miles. Por ejemplo: 150000,50";

type Formulario = { modo: "cerrado" } | { modo: "nuevo" } | { modo: "editar"; bolsillo: Bolsillo };

export function Bolsillos() {
  const [bolsillos, setBolsillos] = useState<Bolsillo[]>([]);
  const [verArchivados, setVerArchivados] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formulario, setFormulario] = useState<Formulario>({ modo: "cerrado" });

  async function cargar() {
    try {
      // Siempre todos (también los archivados): el color de cada meta sigue al bolsillo por
      // orden de creación, y ese orden no debe cambiar al mostrar u ocultar los archivados.
      setBolsillos(await listarBolsillos(true));
    } catch (e) {
      setError(mensajeDe(e));
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar();   // la casilla de archivados solo filtra lo que ya llegó: no vuelve a pedir nada
  }, []);

  function abrirFormulario(nuevo: Formulario) {
    setError(null);
    setFormulario(nuevo);
  }

  async function alGuardar() {
    setFormulario({ modo: "cerrado" });
    await cargar();
  }

  const colores = coloresPorId(bolsillos.map((b) => b.id_bolsillo));   // el mismo color en el resumen y en la tarjeta
  const metas = prepararMetas(bolsillos, colores);
  const mostrados = verArchivados ? bolsillos : bolsillos.filter((b) => b.activo);

  return (
    <section>
      <div className="titulo-con-acciones">
        <h1>Bolsillos</h1>
        {formulario.modo === "cerrado" && (
          <button type="button" onClick={() => abrirFormulario({ modo: "nuevo" })}>Nuevo bolsillo</button>
        )}
      </div>
      <p className="nota">
        Un bolsillo es dinero que aparta mentalmente para algo, sin moverlo de sus cuentas. Lo que reserve
        aquí se resta del <strong>disponible</strong> en el Resumen.
      </p>

      {metas.length > 0 && (
        <div className="tarjeta bloque-grafico">
          <h3>Progreso de las metas</h3>
          <ProgresoMetas filas={metas} />
        </div>
      )}

      {formulario.modo !== "cerrado" && (
        <FormularioBolsillo
          key={formulario.modo === "editar" ? formulario.bolsillo.id_bolsillo : "nuevo"}
          bolsillo={formulario.modo === "editar" ? formulario.bolsillo : null}
          alGuardar={alGuardar}
          alCancelar={() => setFormulario({ modo: "cerrado" })}
        />
      )}

      <label className="casilla">
        <input type="checkbox" checked={verArchivados} onChange={(e) => setVerArchivados(e.target.checked)} />
        Mostrar también los bolsillos archivados
      </label>

      {error && <p className="mensaje-error" role="alert">{error}</p>}

      {cargando ? (
        <p className="cargando">Cargando…</p>
      ) : mostrados.length === 0 ? (
        <p className="vacio">Todavía no tiene bolsillos. Cree el primero con "Nuevo bolsillo".</p>
      ) : (
        <div className="lista-tarjetas anchas">
          {mostrados.map((b) => (
            <TarjetaBolsillo key={b.id_bolsillo} bolsillo={b} color={colores.get(b.id_bolsillo)} alCambiar={cargar}
                             alEditar={() => abrirFormulario({ modo: "editar", bolsillo: b })} />
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Un bolsillo
// ---------------------------------------------------------------------------

interface PropiedadesTarjeta {
  bolsillo: Bolsillo;
  color?: string;   // el color del bolsillo (orden de creación), igual que en "Progreso de las metas"
  alCambiar: () => Promise<void>;
  alEditar: () => void;
}

function TarjetaBolsillo({ bolsillo: b, color, alCambiar, alEditar }: PropiedadesTarjeta) {
  const [cambiando, setCambiando] = useState(false);       // formulario de valor abierto
  const [historial, setHistorial] = useState<ValorBolsillo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function verHistorial() {
    if (historial !== null) {
      setHistorial(null);   // segundo clic: se oculta
      return;
    }
    setError(null);
    try {
      setHistorial(await historialBolsillo(b.id_bolsillo));
    } catch (e) {
      setError(mensajeDe(e));
    }
  }

  async function cambiarEstado() {
    setError(null);
    setAviso(null);
    setOcupado(true);
    try {
      if (b.activo) await archivarBolsillo(b.id_bolsillo);
      else await reactivarBolsillo(b.id_bolsillo);
      await alCambiar();
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "Ya tiene otro bolsillo activo con ese nombre..."
      setOcupado(false);
    }
  }

  async function alGuardarValor(registrado: boolean) {
    setCambiando(false);
    setAviso(registrado ? null : "El valor era el mismo: no se agregó nada al historial.");
    if (historial !== null) setHistorial(await historialBolsillo(b.id_bolsillo));
    await alCambiar();
  }

  const clases = ["tarjeta", "bolsillo", b.activo ? "" : "archivada"];
  return (
    <article className={clases.join(" ").trim()}>
      <div className="cuenta-cabecera">
        <h3>{b.nombre}</h3>
        <span className="etiqueta">{!b.activo ? "Archivado" : b.es_meta ? "Meta" : "Bolsillo"}</span>
      </div>
      {b.descripcion && <p className="ayuda sin-margen">{b.descripcion}</p>}
      <span className="cifra-valor">{formatearDinero(b.valor_actual)}</span>

      {b.es_meta && b.monto_objetivo !== null && b.progreso_porcentaje !== null && (
        <Progreso porcentaje={b.progreso_porcentaje} objetivo={b.monto_objetivo} fecha={b.fecha_objetivo} color={color} />
      )}

      {cambiando && (
        <FormularioValor bolsillo={b} alGuardar={alGuardarValor} alCancelar={() => setCambiando(false)} />
      )}
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}

      {historial !== null && (
        <ul className="historial-valores">
          {historial.map((v, i) => (
            <li key={v.registrado_en + i}>
              <span className="ayuda">{formatearFechaHora(v.registrado_en)}</span>
              <span className="numero">{formatearDinero(v.valor)}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="acciones">
        {b.activo && !cambiando && (
          <button type="button" className="boton-enlace" disabled={ocupado}
                  onClick={() => { setAviso(null); setCambiando(true); }}>
            Cambiar valor
          </button>
        )}
        {b.activo && (
          <button type="button" className="boton-enlace" disabled={ocupado} onClick={alEditar}>Editar</button>
        )}
        <button type="button" className="boton-enlace" disabled={ocupado} onClick={() => void verHistorial()}>
          {historial === null ? "Historial" : "Ocultar historial"}
        </button>
        <button type="button" className="boton-enlace" disabled={ocupado} onClick={() => void cambiarEstado()}>
          {b.activo ? "Archivar" : "Reactivar"}
        </button>
      </div>
    </article>
  );
}

/** Barra de progreso de una meta. El porcentaje viene de la API; puede pasar de 100 (RN-48). */
interface PropiedadesProgreso {
  porcentaje: string;
  objetivo: string;
  fecha: string | null;
  color?: string;
}

function Progreso({ porcentaje, objetivo, fecha, color }: PropiedadesProgreso) {
  // Number() aquí solo decide el ANCHO de la barra (un dibujo), no un valor de dinero.
  const ancho = Math.min(100, Number(porcentaje));
  const cumplida = Number(porcentaje) >= 100;
  return (
    <div className="progreso">
      <div className="barra" role="progressbar" aria-valuenow={ancho} aria-valuemin={0} aria-valuemax={100}
           aria-label={`Progreso: ${formatearPorcentaje(porcentaje)}`}>
        <div className="relleno" style={{ width: `${ancho}%`, background: color }} />
      </div>
      <span className="ayuda">
        {cumplida ? "¡Meta cumplida! " : ""}
        {formatearPorcentaje(porcentaje)} de {formatearDinero(objetivo)}
        {fecha && ` · para el ${formatearFecha(fecha)}`}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cambiar el valor (RN-42: se escribe el valor nuevo, no un aporte ni un retiro)
// ---------------------------------------------------------------------------

interface PropiedadesValor {
  bolsillo: Bolsillo;
  alGuardar: (registrado: boolean) => Promise<void>;
  alCancelar: () => void;
}

function FormularioValor({ bolsillo, alGuardar, alCancelar }: PropiedadesValor) {
  const [valor, setValor] = useState(dineroParaCampo(bolsillo.valor_actual));
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!esDineroValido(valor)) {
      setError(MENSAJE_MONTO);
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      const { registrado } = await cambiarValor(bolsillo.id_bolsillo, dineroParaEnviar(valor));
      await alGuardar(registrado);
    } catch (e) {
      setError(mensajeDe(e));
      setEnviando(false);
    }
  }

  return (
    <form className="formulario-cargo" onSubmit={enviar}>
      <CampoDinero etiqueta="¿Cuánto tiene ahora en este bolsillo?" valor={valor} alCambiar={setValor}
                   ayuda="el total, no lo que agrega" />
      {error && <p className="mensaje-error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar valor"}</button>
        <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>Cancelar</button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Crear o editar un bolsillo
// ---------------------------------------------------------------------------

interface PropiedadesFormulario {
  bolsillo: Bolsillo | null;   // null = nuevo
  alGuardar: () => Promise<void>;
  alCancelar: () => void;
}

function FormularioBolsillo({ bolsillo: b, alGuardar, alCancelar }: PropiedadesFormulario) {
  const [nombre, setNombre] = useState(b?.nombre ?? "");
  const [descripcion, setDescripcion] = useState(b?.descripcion ?? "");
  const [esMeta, setEsMeta] = useState(b?.es_meta ?? false);
  const [montoObjetivo, setMontoObjetivo] = useState(b?.monto_objetivo ? dineroParaCampo(b.monto_objetivo) : "");
  const [fechaObjetivo, setFechaObjetivo] = useState(b?.fecha_objetivo ?? "");
  const [valor, setValor] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if ((esMeta && !esDineroValido(montoObjetivo)) || (b === null && !esDineroValido(valor))) {
      setError(MENSAJE_MONTO);
      return;
    }
    setError(null);
    setEnviando(true);
    // Sin meta: monto y fecha van en null (bolsillo genérico, D-08). La fecha solo con monto (RN-41).
    const datos = {
      nombre,
      descripcion,
      monto_objetivo: esMeta ? dineroParaEnviar(montoObjetivo) : null,
      fecha_objetivo: esMeta && fechaObjetivo ? fechaObjetivo : null,
    };
    try {
      if (b) await editarBolsillo(b.id_bolsillo, datos);
      else await crearBolsillo(datos, dineroParaEnviar(valor));
      await alGuardar();
    } catch (e) {
      setError(mensajeDe(e));   // por ejemplo: "Ya tiene un bolsillo activo con ese nombre."
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta formulario-ancho" onSubmit={enviar}>
      <h2>{b ? `Editar "${b.nombre}"` : "Nuevo bolsillo"}</h2>
      <div className="campos">
        <label>
          Nombre
          <input type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        </label>
        <label>
          Descripción (opcional)
          <input type="text" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </label>
        {b === null && (
          <CampoDinero etiqueta="Valor inicial" valor={valor} alCambiar={setValor} ayuda="lo que ya tiene apartado" />
        )}
      </div>

      <label className="casilla">
        <input type="checkbox" checked={esMeta} onChange={(e) => setEsMeta(e.target.checked)} />
        Es una meta (quiero llegar a un monto)
      </label>
      {esMeta && (
        <div className="campos">
          <CampoDinero etiqueta="Monto objetivo" valor={montoObjetivo} alCambiar={setMontoObjetivo} />
          <label>
            Fecha objetivo (opcional)
            <input type="date" value={fechaObjetivo} onChange={(e) => setFechaObjetivo(e.target.value)} />
          </label>
        </div>
      )}
      {b && <p className="ayuda">El valor se cambia con "Cambiar valor", para que quede en el historial.</p>}

      {error && <p className="mensaje-error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
        <button type="button" className="boton-secundario" onClick={alCancelar} disabled={enviando}>Cancelar</button>
      </div>
    </form>
  );
}
