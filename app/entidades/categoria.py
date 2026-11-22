"""Entidad Categoria: una fila de la tabla categoria (MODELO_DATOS.md, sección 4.3)."""

from dataclasses import dataclass
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
