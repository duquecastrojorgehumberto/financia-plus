// Configuración de Vite (servidor de desarrollo y compilación de la interfaz).
//
// El proxy es la pieza clave (ARQUITECTURA.md, sección 6): el navegador le pide
// todo a Vite (http://localhost:5173), y Vite reenvía a Flask lo que empieza por
// /api. Así la interfaz y la API comparten ORIGEN: la cookie de sesión funciona
// sin configurar CORS, y SameSite=Lax sigue protegiendo contra otros sitios.
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Normalmente la API está en el puerto 5000. Para probar contra otra API (por
// ejemplo, una conectada a la base de pruebas) se define FINANCIA_API antes de
// arrancar:   $env:FINANCIA_API = "http://127.0.0.1:5001"; npm run dev
export default defineConfig(({ mode }) => {
  const api = loadEnv(mode, ".", "FINANCIA_").FINANCIA_API ?? "http://127.0.0.1:5000";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": api,
      },
    },
  };
});
