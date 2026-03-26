"""Parametros tecnicos DNIT para terraplenagem.

Referencia:
    - DNIT 106/2009-ES: Terraplenagem - Cortes
    - DNIT 108/2009-ES: Terraplenagem - Aterros
    - DER/PR Manual de Execucao de Servicos Rodoviarios (2023)
"""

from dataclasses import dataclass, field
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
    espacamento_grade: float = 1.0        # metros entre pontos da grade
    remocao_vegetal: float = 0.30         # metros de camada vegetal
    talude_corte_h: float = 1.0           # componente horizontal (1:1)
    talude_corte_v: float = 1.0           # componente vertical
    talude_aterro_h: float = 2.0          # componente horizontal (1:2)
    talude_aterro_v: float = 1.0          # componente vertical
    categoria_solo: CategoriaSolo = CategoriaSolo.PRIMEIRA


NORMAS_REFERENCIA = {
    "cortes": "DNIT 106/2009-ES",
    "aterros": "DNIT 108/2009-ES",
    "investigacao": "DNIT 381/2022-PRO",
    "tratamento_taludes": "DNIT 074/2006-ES",
}


def obter_fator_empolamento(categoria: CategoriaSolo) -> float:
    """Retorna o fator de empolamento para a categoria de solo."""
    return FATORES_DNIT[categoria].empolamento


def obter_fator_homogeneizacao(categoria: CategoriaSolo) -> float:
    """Retorna o fator de homogeneizacao para a categoria de solo."""
    return FATORES_DNIT[categoria].homogeneizacao


def obter_fator_compactacao(categoria: CategoriaSolo) -> float:
    """Retorna fator compactacao = empolamento * homogeneizacao.

    Converte volume de corte in-situ para volume equivalente de aterro compactado.
    """
    f = FATORES_DNIT[categoria]
    return f.empolamento * f.homogeneizacao
