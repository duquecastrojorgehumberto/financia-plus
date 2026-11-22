"""Fábrica de la aplicación FINANCIA+.

create_app() arma y devuelve la aplicación Flask lista para usar. Se llama
"fábrica" porque cada llamada fabrica una aplicación nueva: el servidor crea
una con la configuración de .env, y las pruebas crean otras con su propia
configuración (base de pruebas), sin variables globales compartidas.

El nombre create_app no está en español a propósito: es el nombre que Flask
busca automáticamente al ejecutar "flask --app app run".
"""

from flask import Flask

from app.bd import BaseDatos, cerrar_conexion
from app.config import Config
from app.csrf import registrar_csrf
from app.errores import registrar_manejadores
from app.rutas.salud import salud_bp


def create_app(config: Config | None = None) -> Flask:
    """Crea la aplicación. Sin argumento, lee la configuración del entorno (.env)."""
    if config is None:
        config = Config.desde_entorno()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.secret_key,
        SESSION_COOKIE_HTTPONLY=True,     # JavaScript no puede leer la cookie de sesión
        SESSION_COOKIE_SAMESITE="Lax",    # otros sitios no la envían en peticiones POST
    )
    app.json.ensure_ascii = False         # respuestas JSON con tildes legibles

    # Un solo objeto BaseDatos para toda la aplicación; cada petición abre su conexión.
    app.extensions["financia_bd"] = BaseDatos(config.database_url)
    app.teardown_appcontext(cerrar_conexion)

    registrar_csrf(app)
    registrar_manejadores(app)
    app.register_blueprint(salud_bp)
    return app
