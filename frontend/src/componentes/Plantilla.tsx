// Marco común de las pantallas con sesión: encabezado, menú y botón de salir.
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";

import { useSesion } from "../sesion/ContextoSesion";

export function Plantilla() {
  const { usuario, cerrarSesion } = useSesion();
  const navegar = useNavigate();
  const [saliendo, setSaliendo] = useState(false);

  async function salir() {
    setSaliendo(true);
    try {
      await cerrarSesion();
      navegar("/iniciar-sesion", { replace: true });
    } finally {
      setSaliendo(false);
    }
  }

  return (
    <div className="plantilla">
      <header className="encabezado">
        <span className="marca">FINANCIA+</span>
        <nav className="menu">
          <NavLink to="/" end>
            Resumen
          </NavLink>
          <NavLink to="/movimientos">Movimientos</NavLink>
          <NavLink to="/transferencias">Transferencias</NavLink>
          <NavLink to="/cuentas">Cuentas</NavLink>
          <NavLink to="/categorias">Categorías</NavLink>
        </nav>
        <div className="usuario">
          <span>{usuario?.nombre}</span>
          <button type="button" className="boton-secundario" onClick={salir} disabled={saliendo}>
            {saliendo ? "Saliendo…" : "Cerrar sesión"}
          </button>
        </div>
      </header>
      <main className="contenido">
        <Outlet />
      </main>
    </div>
  );
}
