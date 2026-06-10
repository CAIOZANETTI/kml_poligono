"""Parametros tecnicos DNIT para terraplenagem.

Referencia:
    - DNIT 106/2009-ES: Terraplenagem - Cortes
    - DNIT 108/2009-ES: Terraplenagem - Aterros
    - DER/PR Manual de Execucao de Servicos Rodoviarios (2023)
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict


class CategoriaSolo(Enum):
    """Categorias de solo conforme DNIT."""
    PRIMEIRA = "1a_categoria"    # Solo
    SEGUNDA = "2a_categoria"     # Rocha alterada
    TERCEIRA = "3a_categoria"    # Rocha


NOMES_CATEGORIA: Dict[CategoriaSolo, str] = {
    CategoriaSolo.PRIMEIRA: "1\u00aa Categoria (Solo)",
    CategoriaSolo.SEGUNDA: "2\u00aa Categoria (Rocha Alterada)",
    CategoriaSolo.TERCEIRA: "3\u00aa Categoria (Rocha)",
}


@dataclass(frozen=True)
class FatoresSolo:
    """Fatores de conversao volumetrica por categoria de solo."""
    empolamento: float
    homogeneizacao: float


FATORES_DNIT: Dict[CategoriaSolo, FatoresSolo] = {
    CategoriaSolo.PRIMEIRA:  FatoresSolo(empolamento=0.77, homogeneizacao=1.00),
    CategoriaSolo.SEGUNDA:   FatoresSolo(empolamento=0.72, homogeneizacao=1.15),
    CategoriaSolo.TERCEIRA:  FatoresSolo(empolamento=0.57, homogeneizacao=1.45),
}


@dataclass
class ParametrosPadrao:
    """Parametros padrao ajustaveis pelo usuario."""
    espacamento_grade: float = 10.0       # metros entre pontos da grade
    remocao_vegetal: float = 0.30         # metros de camada vegetal
    talude_corte_h: float = 1.0           # componente horizontal (1:1)
    talude_corte_v: float = 1.0           # componente vertical
    talude_aterro_h: float = 2.0          # componente horizontal (1:2)
    talude_aterro_v: float = 1.0          # componente vertical
    categoria_solo: CategoriaSolo = CategoriaSolo.PRIMEIRA


def descricao_talude(razao_h: float, razao_v: float) -> str:
    """Retorna '1:N (ângulo°)' a partir das componentes H e V (convenção 1:N)."""
    ratio = razao_h / razao_v
    ang = math.degrees(math.atan(razao_v / razao_h))
    return "1:{:g} ({:.1f}°)".format(ratio, ang)


def premissa_taludes_md(parametros: "ParametrosPadrao") -> str:
    """Texto markdown da premissa de taludes (corte e aterro), reutilizável."""
    corte = descricao_talude(parametros.talude_corte_h, parametros.talude_corte_v)
    aterro = descricao_talude(parametros.talude_aterro_h, parametros.talude_aterro_v)
    return "**Premissa de taludes** — Corte **{}** · Aterro **{}**".format(corte, aterro)


NORMAS_REFERENCIA = {
    "cortes": "DNIT 106/2009-ES",
    "aterros": "DNIT 108/2009-ES",
    "investigacao": "DNIT 381/2022-PRO",
    "tratamento_taludes": "DNIT 074/2006-ES",
}


def _resolver_categoria(categoria) -> CategoriaSolo:
    """Converte string ou enum para CategoriaSolo."""
    if isinstance(categoria, CategoriaSolo):
        return categoria
    if isinstance(categoria, str):
        # Tenta pelo value
        for cat in CategoriaSolo:
            if cat.value == categoria:
                return cat
        # Tenta pelo nome
        try:
            return CategoriaSolo[categoria]
        except KeyError:
            pass
    # Default
    return CategoriaSolo.PRIMEIRA


def obter_fator_empolamento(categoria) -> float:
    """Retorna o fator de empolamento para a categoria de solo."""
    return FATORES_DNIT[_resolver_categoria(categoria)].empolamento


def obter_fator_homogeneizacao(categoria) -> float:
    """Retorna o fator de homogeneizacao para a categoria de solo."""
    return FATORES_DNIT[_resolver_categoria(categoria)].homogeneizacao
