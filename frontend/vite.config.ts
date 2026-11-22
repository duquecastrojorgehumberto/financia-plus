// Configuración de Vite (servidor de desarrollo y compilación de la interfaz).
//
// El proxy es la pieza clave (ARQUITECTURA.md, sección 6): el navegador le pide
// todo a Vite (http://localhost:5173), y Vite reenvía a Flask lo que empieza por
// /api. Así la interfaz y la API comparten ORIGEN: la cookie de sesión funciona
// sin configurar CORS, y SameSite=Lax sigue protegiendo contra otros sitios.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5000",
    },
  },
});
