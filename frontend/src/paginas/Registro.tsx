// Pantalla de registro (RF-01). Al registrarse, la sesión queda iniciada (P-9)
// y el usuario ya tiene sus categorías por defecto (RN-26).
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router";

import { ErrorApi } from "../api/cliente";
import { useSesion } from "../sesion/ContextoSesion";

export function Registro() {
  const { usuario, registrar } = useSesion();
  const navegar = useNavigate();

  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario !== null) {
    return <Navigate to="/" replace />;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await registrar(nombre, correo, clave);
      navegar("/", { replace: true });
    } catch (e) {
      // Las reglas (correo repetido, contraseña corta...) las decide la API; aquí solo se muestra su mensaje.
      setError(e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pagina-acceso">
      <form className="tarjeta formulario" onSubmit={enviar}>
        <h1>Crear cuenta</h1>
        <p className="subtitulo">Recibirá categorías de ingresos y egresos para empezar</p>

        <label>
          Nombre
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="name" required />
        </label>
        <label>
          Correo
          <input type="email" value={correo} onChange={(e) => setCorreo(e.target.value)}
                 autoComplete="email" required />
        </label>
        <label>
          Contraseña
          <input type="password" value={clave} onChange={(e) => setClave(e.target.value)}
                 autoComplete="new-password" minLength={8} required />
          <span className="ayuda">Mínimo 8 caracteres.</span>
        </label>

        {error && <p className="mensaje-error" role="alert">{error}</p>}

        <button type="submit" disabled={enviando}>
          {enviando ? "Creando…" : "Crear cuenta"}
        </button>
        <p className="pie-formulario">
          ¿Ya tiene cuenta? <Link to="/iniciar-sesion">Inicie sesión</Link>
        </p>
      </form>
    </div>
  );
}
