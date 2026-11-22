// Quién tiene la sesión iniciada, disponible para cualquier pantalla.
//
// Un "contexto" de React es un valor que un componente de arriba ofrece y que
// cualquier componente de abajo puede leer con useSesion(), sin pasarlo de
// mano en mano. Aquí el valor es el usuario conectado y las acciones de sesión.
//
// El usuario NO se guarda en el navegador (ni en localStorage): la verdad está
// en la cookie de sesión de Flask. Al abrir la página se le pregunta al
// servidor (GET /api/sesion) si la cookie sigue siendo válida.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import * as apiSesion from "../api/sesion";
import type { Usuario } from "../api/tipos";

interface ValorSesion {
  usuario: Usuario | null;
  /** true mientras se pregunta al servidor si hay sesión (al abrir la página). */
  cargando: boolean;
  iniciarSesion: (correo: string, clave: string) => Promise<void>;
  registrar: (nombre: string, correo: string, clave: string) => Promise<void>;
  cerrarSesion: () => Promise<void>;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    apiSesion
      .consultarSesion()
      .then(setUsuario)
      .catch(() => setUsuario(null))   // 401: no hay sesión
      .finally(() => setCargando(false));
  }, []);

  const valor: ValorSesion = {
    usuario,
    cargando,
    iniciarSesion: async (correo, clave) => setUsuario(await apiSesion.iniciarSesion(correo, clave)),
    registrar: async (nombre, correo, clave) => setUsuario(await apiSesion.registrar(nombre, correo, clave)),
    cerrarSesion: async () => {
      await apiSesion.cerrarSesion();
      setUsuario(null);
    },
  };

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (valor === null) {
    throw new Error("useSesion debe usarse dentro de <ProveedorSesion>.");
  }
  return valor;
}
