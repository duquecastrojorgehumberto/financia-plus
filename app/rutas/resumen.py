"""Ruta del resumen financiero (RF-13, RF-15). Exige sesión.

    GET /api/resumen                                 -> el mes actual
    GET /api/resumen?desde=2026-11-01&hasta=2026-11-30

    200 {
      "indicadores": {saldo_total, total_reservado, disponible, disponible_negativo},
      "periodo": {
        desde, hasta, ingresos, egresos, balance,
        ajustes: {aumentos, disminuciones},                 aparte (RN-53)
        categorias: {
          ingresos: [{id_categoria, nombre, total, directo, subcategorias: [...]}, ...],
          egresos:  [...]                                   cada raíz con sus subcategorías (RN-27)
        }
      }
    }

Los indicadores son del momento actual (no dependen del periodo). Todo el dinero
viaja como texto ("130000.00").
"""

from flask import Blueprint, jsonify

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.resumen import ResumenServicio
from app.sesion import requiere_sesion

resumen_bp = Blueprint("resumen", __name__, url_prefix="/api/resumen")


@resumen_bp.get("")
@requiere_sesion
def resumen(id_usuario):
    servicio = ResumenServicio(obtener_conexion())
    periodo = servicio.periodo(id_usuario, entrada.parametro_fecha("desde"), entrada.parametro_fecha("hasta"))
    return jsonify(indicadores=servicio.indicadores(id_usuario).datos_publicos(),
                   periodo=periodo.datos_publicos())
