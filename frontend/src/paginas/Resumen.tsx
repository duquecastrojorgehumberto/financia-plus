// Pantalla de resumen financiero (RF-13, RF-15).
//
// Arriba, los indicadores del momento: saldo total, total reservado y disponible,
// con un aviso si el disponible es negativo (RN-63: se avisa, no se bloquea nada).
// Abajo, el periodo elegido: ingresos, egresos, balance, los ajustes aparte
// (RN-53) y los totales por categoría con sus subcategorías (RN-27).
//
// La pantalla no calcula nada: todos los números vienen ya calculados de la API.
import { useEffect, useState, type FormEvent } from "react";

import { ErrorApi } from "../api/cliente";
import { consultarResumen } from "../api/resumen";
import type { RespuestaResumen, TotalCategoria } from "../api/tipos";
import { esNegativo, formatearDinero, formatearFecha } from "../util/formato";

export function Resumen() {
  const [resumen, setResumen] = useState<RespuestaResumen | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  async function cargar(fechaDesde?: string, fechaHasta?: string) {
    setCargando(true);
    setError(null);
    try {
      const datos = await consultarResumen(fechaDesde, fechaHasta);
      setResumen(datos);
      setDesde(datos.periodo.desde);   // muestra en el formulario el periodo que usó la API
      setHasta(datos.periodo.hasta);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo cargar el resumen.");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar();   // al abrir: el mes actual
  }, []);

  function cambiarPeriodo(evento: FormEvent) {
    evento.preventDefault();
    void cargar(desde, hasta);
  }

  return (
    <section>
      <h1>Resumen</h1>

      {resumen && <Indicadores datos={resumen.indicadores} />}

      <form className="filtro-periodo" onSubmit={cambiarPeriodo}>
        <label>
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required />
        </label>
        <label>
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} required />
        </label>
        <button type="submit" disabled={cargando}>
          {cargando ? "Cargando…" : "Ver periodo"}
        </button>
      </form>

      {error && <p className="mensaje-error" role="alert">{error}</p>}
      {resumen && <Periodo datos={resumen.periodo} />}
    </section>
  );
}

function Indicadores({ datos }: { datos: RespuestaResumen["indicadores"] }) {
  return (
    <>
      <div className="indicadores">
        <Cifra titulo="Saldo total de cuentas" valor={datos.saldo_total} />
        <Cifra titulo="Reservado en bolsillos" valor={datos.total_reservado} />
        <Cifra titulo="Disponible no reservado" valor={datos.disponible} destacar />
      </div>
      {datos.disponible_negativo && (
        <p className="aviso" role="status">
          Tiene reservado más dinero del que hay en sus cuentas. No se bloquea nada, pero revise sus bolsillos.
        </p>
      )}
    </>
  );
}

function Periodo({ datos }: { datos: RespuestaResumen["periodo"] }) {
  const hayAjustes = !(datos.ajustes.aumentos === "0.00" && datos.ajustes.disminuciones === "0.00");
  return (
    <>
      <h2>
        Del {formatearFecha(datos.desde)} al {formatearFecha(datos.hasta)}
      </h2>
      <div className="indicadores">
        <Cifra titulo="Ingresos" valor={datos.ingresos} />
        <Cifra titulo="Egresos" valor={datos.egresos} />
        <Cifra titulo="Balance" valor={datos.balance} destacar />
      </div>
      {hayAjustes && (
        <p className="nota">
          Ajustes de saldo en el periodo (no cuentan como ingresos ni egresos):
          aumentos {formatearDinero(datos.ajustes.aumentos)}, disminuciones{" "}
          {formatearDinero(datos.ajustes.disminuciones)}.
        </p>
      )}
      <div className="columnas">
        <TablaCategorias titulo="Egresos por categoría" categorias={datos.categorias.egresos} />
        <TablaCategorias titulo="Ingresos por categoría" categorias={datos.categorias.ingresos} />
      </div>
    </>
  );
}

function Cifra({ titulo, valor, destacar = false }: { titulo: string; valor: string; destacar?: boolean }) {
  const clases = ["tarjeta", "cifra", destacar ? "destacada" : "", esNegativo(valor) ? "negativa" : ""];
  return (
    <div className={clases.join(" ").trim()}>
      <span className="cifra-titulo">{titulo}</span>
      <span className="cifra-valor">{formatearDinero(valor)}</span>
    </div>
  );
}

function TablaCategorias({ titulo, categorias }: { titulo: string; categorias: TotalCategoria[] }) {
  return (
    <div className="tarjeta">
      <h3>{titulo}</h3>
      {categorias.length === 0 ? (
        <p className="vacio">No hay movimientos en este periodo.</p>
      ) : (
        <table className="tabla">
          <tbody>
            {categorias.map((c) => (
              <FilasCategoria key={c.id_categoria} categoria={c} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Una raíz y, debajo, sus subcategorías. Si también tiene movimientos propios, se muestran como "(directo)". */
function FilasCategoria({ categoria }: { categoria: TotalCategoria }) {
  const tieneDirecto = categoria.directo !== "0.00" && categoria.subcategorias.length > 0;
  return (
    <>
      <tr className="fila-raiz">
        <td>{categoria.nombre}</td>
        <td className="numero">{formatearDinero(categoria.total)}</td>
      </tr>
      {tieneDirecto && (
        <tr className="fila-sub">
          <td>{categoria.nombre} (directo)</td>
          <td className="numero">{formatearDinero(categoria.directo)}</td>
        </tr>
      )}
      {categoria.subcategorias.map((s) => (
        <tr key={s.id_categoria} className="fila-sub">
          <td>{s.nombre}</td>
          <td className="numero">{formatearDinero(s.total)}</td>
        </tr>
      ))}
    </>
  );
}
