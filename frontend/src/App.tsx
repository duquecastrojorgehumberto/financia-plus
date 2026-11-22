// Las pantallas de la aplicación y qué dirección (URL) muestra cada una.
//
//   /iniciar-sesion   y   /registro       sin sesión
//   /                  Resumen             con sesión (RutaProtegida), dentro de la Plantilla
//
// Las pantallas de cuentas, categorías, movimientos, transferencias, ajustes y
// bolsillos se agregarán aquí, también dentro de RutaProtegida y Plantilla.
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { Plantilla } from "./componentes/Plantilla";
import { RutaProtegida } from "./componentes/RutaProtegida";
import { IniciarSesion } from "./paginas/IniciarSesion";
import { Registro } from "./paginas/Registro";
import { Resumen } from "./paginas/Resumen";
import { ProveedorSesion } from "./sesion/ContextoSesion";

export function App() {
  return (
    <ProveedorSesion>
      <BrowserRouter>
        <Routes>
          <Route path="/iniciar-sesion" element={<IniciarSesion />} />
          <Route path="/registro" element={<Registro />} />
          <Route element={<RutaProtegida />}>
            <Route element={<Plantilla />}>
              <Route path="/" element={<Resumen />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ProveedorSesion>
  );
}
