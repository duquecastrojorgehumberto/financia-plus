// Envuelve las pantallas que exigen sesión. Es el equivalente en la interfaz
// del decorador @requiere_sesion de Flask, pero solo por comodidad: la
// protección real está en la API, que responde 401 sin sesión.
import { Navigate, Outlet, useLocation } from "react-router";

import { useSesion } from "../sesion/ContextoSesion";

export function RutaProtegida() {
  const { usuario, cargando } = useSesion();
  const ubicacion = useLocation();

  if (cargando) {
    return <p className="cargando">Cargando…</p>;
  }
  if (usuario === null) {
    // Después de iniciar sesión, se vuelve a la página que se quería ver.
    return <Navigate to="/iniciar-sesion" replace state={{ desde: ubicacion.pathname }} />;
  }
  return <Outlet />;
}
