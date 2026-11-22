"""Ruta del resumen financiero (RF-13, RF-15). Exige sesión.

    GET /api/resumen                                 -> el mes actual
    GET /api/resumen?desde=2026-11-01&hasta=2026-11-30

    200 {
      "indicadores": {saldo_total, total_reservado, disponible, disponible_negativo},
      "periodo": {
        desde, hasta, ingresos, egresos, balance,
        ajustes: {aumentos, disminuciones},                 aparte (RN-53)
        categorias: {
          ingresos: [{id_categoria, nombre, total, porcentaje, directo, porcentaje_directo,
                      subcategorias: [{id_categoria, nombre, total, porcentaje}, ...]}, ...],
          egresos:  [...]                                   cada raíz con sus subcategorías (RN-27)
        }
      }
    }
    porcentaje: "35.5" (un decimal), sobre el total del tipo (todas las raíces de ingreso, o de egreso).

    GET /api/resumen/mensual                         -> los últimos 6 meses, hasta el actual
    GET /api/resumen/mensual?meses=12                -> de 1 a 24 meses

    200 {"meses": [{mes: "2026-06", ingresos, egresos, balance}, ...]}
        del más antiguo al más reciente; los meses sin movimientos vienen con "0.00".

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


@resumen_bp.get("/mensual")
@requiere_sesion
def mensual(id_usuario):
    meses = entrada.parametro_entero("meses")
    totales = ResumenServicio(obtener_conexion()).mensual(id_usuario, meses if meses is not None else 6)
    return jsonify(meses=[t.datos_publicos() for t in totales])
