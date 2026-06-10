"""Parametros tecnicos para terraplenagem.

Os volumes calculados sao GEOMETRICOS (in-situ): corte e aterro medidos
contra o terreno natural, sem fatores de conversao de material
(empolamento/contracao). A conversao depende do material real de cada
trecho (solo, rocha alterada, rocha, misturas) e pertence a uma analise
de materiais especifica, fora do escopo deste calculo.

Referencia:
    - DNIT 106/2009-ES: Terraplenagem - Cortes
    - DNIT 108/2009-ES: Terraplenagem - Aterros
    - DER/PR Manual de Execucao de Servicos Rodoviarios (2023)
"""

import math
from dataclasses import dataclass


@dataclass
class ParametrosPadrao:
    """Parametros padrao ajustaveis pelo usuario."""
    espacamento_grade: float = 10.0       # metros entre pontos da grade
    remocao_vegetal: float = 0.30         # metros de camada vegetal
    talude_corte_h: float = 1.0           # componente horizontal (1:1)
    talude_corte_v: float = 1.0           # componente vertical
    talude_aterro_h: float = 2.0          # componente horizontal (1:2)
    talude_aterro_v: float = 1.0          # componente vertical


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
