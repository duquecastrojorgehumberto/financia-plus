// Pantalla de inicio de sesión (RF-01).
import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";

import { ErrorApi } from "../api/cliente";
import { useSesion } from "../sesion/ContextoSesion";

export function IniciarSesion() {
  const { usuario, iniciarSesion } = useSesion();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const destino = (ubicacion.state as { desde?: string } | null)?.desde ?? "/";

  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario !== null) {
    return <Navigate to={destino} replace />;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);   // el botón se deshabilita: evita el doble envío (ARQUITECTURA.md, sección 7)
    try {
      await iniciarSesion(correo, clave);
      navegar(destino, { replace: true });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "Ocurrió un error inesperado.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pagina-acceso">
      <form className="tarjeta formulario" onSubmit={enviar}>
        <h1>FINANCIA+</h1>
        <p className="subtitulo">Inicie sesión para ver sus finanzas</p>

        <label>
          Correo
          <input type="email" value={correo} onChange={(e) => setCorreo(e.target.value)}
                 autoComplete="email" required />
        </label>
        <label>
          Contraseña
          <input type="password" value={clave} onChange={(e) => setClave(e.target.value)}
                 autoComplete="current-password" required />
        </label>

        {error && <p className="mensaje-error" role="alert">{error}</p>}

        <button type="submit" disabled={enviando}>
          {enviando ? "Entrando…" : "Iniciar sesión"}
        </button>
        <p className="pie-formulario">
          ¿No tiene cuenta? <Link to="/registro">Regístrese</Link>
        </p>
      </form>
    </div>
  );
}
