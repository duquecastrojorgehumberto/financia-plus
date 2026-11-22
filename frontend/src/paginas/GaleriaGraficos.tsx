// PÁGINA TEMPORAL: galería de variantes de los gráficos, para que el estudiante elija.
// Se borra en la etapa 3, cuando las variantes elegidas pasen al Resumen y a Bolsillos.
// Usa los datos reales del usuario. Dirección: /galeria-graficos (con sesión).
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { listarBolsillos } from "../api/bolsillos";
import { listarCategorias } from "../api/categorias";
import { ErrorApi } from "../api/cliente";
import { consultarMensual, consultarResumen } from "../api/resumen";
import type { Bolsillo, RamaCategoria, RespuestaResumen, TotalMes } from "../api/tipos";
import { coloresPorId } from "../graficos/colores";
import { prepararCategorias, prepararMeses, prepararMetas } from "../graficos/datos";
import { GraficoCategorias } from "../graficos/GraficoCategorias";
import { GraficoDona } from "../graficos/GraficoDona";
import { GraficoMensual } from "../graficos/GraficoMensual";
import { ProgresoMetas } from "../graficos/ProgresoMetas";
import { formatearFecha, hoy } from "../util/formato";

/** Del primer día de hace 5 meses al último día del mes actual: 6 meses completos. */
function ultimosSeisMeses(): [string, string] {
  const [anio, mes] = hoy().split("-").map(Number);
  const inicio = new Date(anio, mes - 6, 1);
  const fin = new Date(anio, mes, 0);
  const texto = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return [texto(inicio), texto(fin)];
}

interface Datos {
  resumen: RespuestaResumen;
  meses: TotalMes[];
  bolsillos: Bolsillo[];
  categoriasEgreso: RamaCategoria[];
}

export function GaleriaGraficos() {
  const [inicial, final] = ultimosSeisMeses();
  const [desde, setDesde] = useState(inicial);
  const [hasta, setHasta] = useState(final);
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function cargar(d: string, h: string) {
    setError(null);
    try {
      const [resumen, meses, bolsillos, categoriasEgreso] = await Promise.all([
        consultarResumen(d, h), consultarMensual(6), listarBolsillos(true), listarCategorias("EGRESO", true),
      ]);
      setDatos({ resumen, meses, bolsillos, categoriasEgreso });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudieron cargar los datos.");
    }
  }

  useEffect(() => {
    void cargar(inicial, final);
  }, []);

  function cambiarPeriodo(evento: FormEvent) {
    evento.preventDefault();
    void cargar(desde, hasta);
  }

  if (datos === null) {
    return error ? <p className="mensaje-error" role="alert">{error}</p> : <p className="cargando">Cargando…</p>;
  }

  // Colores: siguen a la categoría (y al bolsillo) por orden de creación.
  const coloresCategorias = coloresPorId(datos.categoriasEgreso.map((r) => r.id_categoria));
  const coloresBolsillos = coloresPorId(datos.bolsillos.map((b) => b.id_bolsillo));
  const categorias = prepararCategorias(datos.resumen.periodo.categorias.egresos, coloresCategorias);
  const meses = prepararMeses(datos.meses);
  const metas = prepararMetas(datos.bolsillos, coloresBolsillos);
  const periodo = `del ${formatearFecha(datos.resumen.periodo.desde)} al ${formatearFecha(datos.resumen.periodo.hasta)}`;

  return (
    <section className="galeria">
      <h1>Galería de gráficos <span className="etiqueta">temporal</span></h1>
      <p className="nota">
        Elija una variante de cada gráfico (por su letra). Todos usan sus datos reales. Pase el mouse (o toque)
        sobre los gráficos para ver el detalle. Esta página se borra cuando los gráficos elegidos pasen al Resumen.
      </p>

      <form className="filtro-periodo" onSubmit={cambiarPeriodo}>
        <label>
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required />
        </label>
        <label>
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} required />
        </label>
        <button type="submit">Ver periodo</button>
      </form>
      {error && <p className="mensaje-error" role="alert">{error}</p>}

      <h2>1. Egresos por categoría <span className="subtitulo">({periodo})</span></h2>
      {categorias.length === 0 ? (
        <p className="vacio">No hay egresos en este periodo.</p>
      ) : (
        <>
          <Variante letra="A" titulo="Nombre a la izquierda, cifras al final de la barra">
            <GraficoCategorias filas={categorias} variante="A" />
          </Variante>
          <Variante letra="B" titulo="Nombre y cifras encima de una barra delgada">
            <GraficoCategorias filas={categorias} variante="B" />
          </Variante>
          <Variante letra="C" titulo="Barras sobre una pista gris, con cuadrícula suave">
            <GraficoCategorias filas={categorias} variante="C" />
          </Variante>
        </>
      )}

      <h2>2. Ingresos vs egresos <span className="subtitulo">(últimos 6 meses)</span></h2>
      <Variante letra="A" titulo="Cuadrícula punteada, eje con montos y leyenda arriba">
        <GraficoMensual filas={meses} variante="A" />
      </Variante>
      <Variante letra="B" titulo="Minimalista: sin cuadrícula ni eje (las cifras, en el tooltip)">
        <GraficoMensual filas={meses} variante="B" />
      </Variante>
      <Variante letra="C" titulo="Como A, con una línea del balance de cada mes">
        <GraficoMensual filas={meses} variante="C" />
      </Variante>

      <h2>3. Distribución de egresos <span className="subtitulo">(opcional: dona o solo las barras de la sección 1)</span></h2>
      {categorias.length === 0 ? (
        <p className="vacio">No hay egresos en este periodo.</p>
      ) : (
        <>
          <Variante letra="A" titulo="Anillo grueso, leyenda al lado">
            <GraficoDona filas={categorias} total={datos.resumen.periodo.egresos} variante="A" />
          </Variante>
          <Variante letra="B" titulo="Anillo delgado con esquinas redondeadas, leyenda debajo">
            <GraficoDona filas={categorias} total={datos.resumen.periodo.egresos} variante="B" />
          </Variante>
        </>
      )}

      <h2>4. Progreso de los bolsillos con meta</h2>
      <Variante letra="A" titulo="Barras con pista, nombre y cifras encima">
        <ProgresoMetas filas={metas} variante="A" />
      </Variante>
      <Variante letra="B" titulo="Anillos, uno por meta, con la lista al lado">
        <ProgresoMetas filas={metas} variante="B" />
      </Variante>
      <Variante letra="C" titulo="Tarjetas con barra; el detalle al pasar el mouse o tocar">
        <ProgresoMetas filas={metas} variante="C" />
      </Variante>
    </section>
  );
}

function Variante({ letra, titulo, children }: { letra: string; titulo: string; children: ReactNode }) {
  return (
    <article className="tarjeta variante">
      <header className="variante-cabecera">
        <span className="variante-letra">{letra}</span>
        <span>Variante {letra}: {titulo}</span>
      </header>
      {children}
    </article>
  );
}
