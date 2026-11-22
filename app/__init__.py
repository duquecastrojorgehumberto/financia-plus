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
from app.rutas.ajustes import ajustes_bp
from app.rutas.autenticacion import autenticacion_bp
from app.rutas.bolsillos import bolsillos_bp
from app.rutas.categorias import categorias_bp
from app.rutas.cuentas import cuentas_bp
from app.rutas.movimientos import movimientos_bp
from app.rutas.salud import salud_bp
from app.rutas.transferencias import transferencias_bp


def create_app(config: Config | None = None, bd: BaseDatos | None = None) -> Flask:
    """Crea la aplicación.

    Sin argumentos, lee la configuración del entorno (.env) y se conecta a la
    base de DATABASE_URL. Las pruebas pueden pasar su propia configuración y su
    propio objeto BaseDatos.
    """
    if config is None:
        config = Config.desde_entorno()
    if bd is None:
        bd = BaseDatos(config.database_url)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.secret_key,
        SESSION_COOKIE_HTTPONLY=True,     # JavaScript no puede leer la cookie de sesión
        SESSION_COOKIE_SAMESITE="Lax",    # otros sitios no la envían en peticiones POST
    )
    app.json.ensure_ascii = False         # respuestas JSON con tildes legibles

    # Un solo objeto BaseDatos para toda la aplicación; cada petición abre su conexión.
    app.extensions["financia_bd"] = bd
    app.teardown_appcontext(cerrar_conexion)

    registrar_csrf(app)
    registrar_manejadores(app)
    app.register_blueprint(salud_bp)
    app.register_blueprint(autenticacion_bp)
    app.register_blueprint(cuentas_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(movimientos_bp)
    app.register_blueprint(transferencias_bp)
    app.register_blueprint(ajustes_bp)
    app.register_blueprint(bolsillos_bp)
    return app
