"""Entidad Categoria: una fila de la tabla categoria (MODELO_DATOS.md, sección 4.3).

Además, RamaCategoria agrupa una categoría raíz con sus subcategorías, para
mostrarlas como árbol de dos niveles (RN-21). Igual que CuentaConSaldo, no
hereda: CONTIENE categorías (composición).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TipoCategoria(StrEnum):
    """Valores permitidos por el CHECK ck_categoria_tipo (RN-20).

    Es un StrEnum: cada valor ES un texto ("INGRESO"), así que se guarda en la
    base y se compara con texto sin conversiones.
    """

    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


@dataclass(frozen=True)
class Categoria:
    id_categoria: int
    id_usuario: int
    id_padre: int | None
    nombre: str
    tipo: TipoCategoria
    activa: bool
    creado_en: datetime

    def es_subcategoria(self) -> bool:
        """True si tiene padre (segundo nivel, RN-21)."""
        return self.id_padre is not None

    def datos_publicos(self) -> dict:
        return {
            "id_categoria": self.id_categoria,
            "id_padre": self.id_padre,
            "nombre": self.nombre,
            "tipo": str(self.tipo),
            "activa": self.activa,
        }


@dataclass(frozen=True)
class RamaCategoria:
    """Una categoría raíz y sus subcategorías."""

    raiz: Categoria
    subcategorias: list[Categoria] = field(default_factory=list)

    def datos_publicos(self) -> dict:
        return {**self.raiz.datos_publicos(),
                "subcategorias": [s.datos_publicos() for s in self.subcategorias]}
