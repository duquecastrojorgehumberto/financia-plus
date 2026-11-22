// Llamadas a la API de sesión (app/rutas/autenticacion.py).
import { api } from "./cliente";
import type { RespuestaUsuario, Usuario } from "./tipos";

export async function consultarSesion(): Promise<Usuario> {
  return (await api.get<RespuestaUsuario>("/sesion")).usuario;
}

export async function iniciarSesion(correo: string, clave: string): Promise<Usuario> {
  return (await api.post<RespuestaUsuario>("/sesion", { correo, clave })).usuario;
}

/** El registro deja la sesión iniciada (P-9). */
export async function registrar(nombre: string, correo: string, clave: string): Promise<Usuario> {
  return (await api.post<RespuestaUsuario>("/registro", { nombre, correo, clave })).usuario;
}

export async function cerrarSesion(): Promise<void> {
  await api.delete("/sesion");
}
