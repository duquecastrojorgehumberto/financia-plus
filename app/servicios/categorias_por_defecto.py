"""Categorías que recibe cada usuario nuevo al registrarse (RN-26).

Es la lista de db/semillas/LEEME.md. Está en Python, y no en un archivo .sql,
porque se copia para CADA usuario dentro de la transacción del registro, con
su id_usuario; no es un dato que se cargue una sola vez en la base.

Formato: tipo -> lista de (categoría, [subcategorías]).
"""

from app.entidades.categoria import TipoCategoria

CATEGORIAS_POR_DEFECTO: dict[TipoCategoria, list[tuple[str, list[str]]]] = {
    TipoCategoria.INGRESO: [
        ("Salario", ["Sueldo", "Primas y bonificaciones"]),
        ("Trabajo independiente", []),
        ("Rendimientos", []),
        ("Otros ingresos", ["Regalos", "Reembolsos"]),
    ],
    TipoCategoria.EGRESO: [
        ("Alimentación", ["Mercado", "Restaurantes", "Domicilios"]),
        ("Vivienda", ["Arriendo", "Servicios públicos", "Hogar y aseo"]),
        ("Transporte", ["Transporte público", "Combustible", "Taxis y aplicaciones"]),
        ("Salud", ["Medicamentos", "Consultas"]),
        ("Educación", ["Matrículas", "Libros y cursos"]),
        ("Entretenimiento", ["Suscripciones", "Salidas"]),
        ("Ropa y cuidado personal", []),
        # Debe existir siempre: se propone para los cargos de las transferencias (RN-26).
        ("Impuestos y comisiones", ["4×1.000", "Comisiones bancarias"]),
        ("Otros gastos", []),
    ],
}
