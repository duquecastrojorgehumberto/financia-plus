// Las pantallas de la aplicación y qué dirección (URL) muestra cada una.
//
//   /iniciar-sesion   y   /registro       sin sesión
//   /                  Resumen             con sesión (RutaProtegida), dentro de la Plantilla
//   /cuentas           Cuentas             con sesión
//   /categorias        Categorias          con sesión
//   /movimientos       Movimientos         con sesión
//   /transferencias    Transferencias      con sesión
//   /ajustes           Ajustes             con sesión
//   /bolsillos         Bolsillos           con sesión
//
// Cualquier otra dirección lleva al Resumen.
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { Plantilla } from "./componentes/Plantilla";
import { RutaProtegida } from "./componentes/RutaProtegida";
import { Ajustes } from "./paginas/Ajustes";
import { Bolsillos } from "./paginas/Bolsillos";
import { Categorias } from "./paginas/Categorias";
import { Cuentas } from "./paginas/Cuentas";
import { GaleriaGraficos } from "./paginas/GaleriaGraficos";
import { IniciarSesion } from "./paginas/IniciarSesion";
import { Movimientos } from "./paginas/Movimientos";
import { Registro } from "./paginas/Registro";
import { Resumen } from "./paginas/Resumen";
import { Transferencias } from "./paginas/Transferencias";
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
              <Route path="/cuentas" element={<Cuentas />} />
              <Route path="/categorias" element={<Categorias />} />
              <Route path="/movimientos" element={<Movimientos />} />
              <Route path="/transferencias" element={<Transferencias />} />
              <Route path="/ajustes" element={<Ajustes />} />
              <Route path="/bolsillos" element={<Bolsillos />} />
              {/* TEMPORAL (gráficos, etapa 2): se borra al integrar las variantes elegidas. */}
              <Route path="/galeria-graficos" element={<GaleriaGraficos />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ProveedorSesion>
  );
}
