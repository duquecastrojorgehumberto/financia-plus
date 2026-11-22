"""Rutas de categorías (RF-03). Todas exigen sesión.

    GET  /api/categorias                       -> 200 {categorias: [raíz con subcategorias]}  solo activas
    GET  /api/categorias?tipo=EGRESO           -> solo las de ese tipo
    GET  /api/categorias?inactivas=1           -> también las desactivadas
    POST /api/categorias                       -> 201 {categoria}
            raíz:          {nombre, tipo}
            subcategoría:  {nombre, id_padre}      (el tipo sale del padre)
    GET  /api/categorias/<id>                  -> 200 {categoria}
    PUT  /api/categorias/<id>                  -> 200 {categoria}   {nombre}: solo el nombre cambia (RN-22)
    POST /api/categorias/<id>/desactivar       -> 200 {categoria, subcategorias_desactivadas}
    POST /api/categorias/<id>/reactivar        -> 200 {categoria}

Una categoría de otro usuario responde 404 (RN-06).
"""

from flask import Blueprint, jsonify, request

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.categorias import CategoriaServicio
from app.sesion import requiere_sesion

categorias_bp = Blueprint("categorias", __name__, url_prefix="/api/categorias")


def _servicio() -> CategoriaServicio:
    return CategoriaServicio(obtener_conexion())


@categorias_bp.get("")
@requiere_sesion
def listar(id_usuario):
    tipo = request.args.get("tipo") or None
    incluir_inactivas = request.args.get("inactivas", "").lower() in ("1", "true", "si", "sí")
    ramas = _servicio().listar_arbol(id_usuario, tipo, incluir_inactivas)
    return jsonify(categorias=[r.datos_publicos() for r in ramas])


@categorias_bp.post("")
@requiere_sesion
def crear(id_usuario):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, "nombre", "tipo", "id_padre")
    tipo = entrada.texto(datos, "tipo") if datos.get("tipo") is not None else None
    categoria = _servicio().crear(id_usuario, entrada.texto(datos, "nombre"), tipo,
                                  entrada.entero_opcional(datos, "id_padre"))
    return jsonify(categoria=categoria.datos_publicos()), 201


@categorias_bp.get("/<int:id_categoria>")
@requiere_sesion
def ver(id_usuario, id_categoria):
    return jsonify(categoria=_servicio().obtener(id_usuario, id_categoria).datos_publicos())


@categorias_bp.put("/<int:id_categoria>")
@requiere_sesion
def renombrar(id_usuario, id_categoria):
    datos = entrada.leer_cuerpo()
    # RN-22: el padre y el tipo no cambian; si llegan, se rechaza en lugar de ignorarlos.
    entrada.solo_campos(datos, "nombre")
    categoria = _servicio().renombrar(id_usuario, id_categoria, entrada.texto(datos, "nombre"))
    return jsonify(categoria=categoria.datos_publicos())


@categorias_bp.post("/<int:id_categoria>/desactivar")
@requiere_sesion
def desactivar(id_usuario, id_categoria):
    categoria, subcategorias = _servicio().desactivar(id_usuario, id_categoria)
    return jsonify(categoria=categoria.datos_publicos(), subcategorias_desactivadas=subcategorias)


@categorias_bp.post("/<int:id_categoria>/reactivar")
@requiere_sesion
def reactivar(id_usuario, id_categoria):
    return jsonify(categoria=_servicio().reactivar(id_usuario, id_categoria).datos_publicos())
