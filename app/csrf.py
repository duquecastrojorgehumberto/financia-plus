"""Protección contra CSRF (ARQUITECTURA.md, sección 6).

El ataque: una página de otro sitio hace que el navegador del usuario, que ya
tiene la cookie de sesión de FINANCIA+, envíe una petición que modifica datos.

La defensa: toda petición que modifica datos (POST, PUT, PATCH, DELETE) debe
  1. llegar con Content-Type: application/json, y
  2. traer el encabezado X-Requested-With: financia.
Un formulario HTML de otro sitio no puede enviar JSON ni encabezados propios,
y un script de otro sitio no puede agregarlos sin permiso CORS (que no damos).
Junto con la cookie SameSite=Lax, cubre el riesgo.

Las peticiones de solo lectura (GET, HEAD, OPTIONS) no se revisan.
"""

from flask import Flask, jsonify, request

METODOS_DE_LECTURA = {"GET", "HEAD", "OPTIONS"}
ENCABEZADO = "X-Requested-With"
VALOR_ESPERADO = "financia"


def verificar_peticion():
    """Se ejecuta antes de cada petición. Si devuelve una respuesta, Flask no llama a la ruta."""
    if request.method in METODOS_DE_LECTURA:
        return None
    if not request.is_json:
        return jsonify(error="La petición debe enviarse en formato JSON."), 415
    if request.headers.get(ENCABEZADO) != VALOR_ESPERADO:
        return jsonify(error="Petición rechazada por seguridad."), 403
    return None


def registrar_csrf(app: Flask) -> None:
    app.before_request(verificar_peticion)
