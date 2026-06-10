"""Calculo de taludes de corte e aterro nas bordas do poligono."""

import numpy as np

from modulos.geometria import GradePoligono
from modulos.terreno import SuperficieTerreno


def identificar_celulas_borda(grade: GradePoligono) -> np.ndarray:
    """Identifica pontos da grade que estao na borda do poligono.

    Um ponto e de borda se algum vizinho (4-conectividade) esta
    fora do poligono ou nao existe na grade.

    Implementacao vetorizada: mapeia os pontos para indices inteiros da
    malha regular (sao multiplos exatos do espacamento) e verifica os
    vizinhos por deslocamento de matriz booleana.

    Returns:
        Array booleano (M,) marcando celulas de borda.
    """
    pontos = grade.pontos_grade
    n = len(pontos)
    if n == 0:
        return np.zeros(0, dtype=bool)

    esp = grade.espacamento
    x0 = pontos[:, 0].min()
    y0 = pontos[:, 1].min()
    ix = np.rint((pontos[:, 0] - x0) / esp).astype(np.int64)
    iy = np.rint((pontos[:, 1] - y0) / esp).astype(np.int64)

    # Matriz de ocupacao com moldura de 1 celula (vizinho fora = inexistente)
    occ = np.zeros((iy.max() + 3, ix.max() + 3), dtype=bool)
    occ[iy + 1, ix + 1] = True

    tem_4_vizinhos = (
        occ[2:, 1:-1] & occ[:-2, 1:-1] & occ[1:-1, 2:] & occ[1:-1, :-2]
    )
    borda_grid = occ[1:-1, 1:-1] & ~tem_4_vizinhos
    return borda_grid[iy, ix]


def calcular_volume_talude_corte(
    grade: GradePoligono,
    superficie: SuperficieTerreno,
    cota_projeto: float,
    inclinacao_h: float = 1.0,
    inclinacao_v: float = 1.0,
    remocao_vegetal: float = 0.30,
    borda: np.ndarray = None,
) -> float:
    """Calcula volume adicional dos taludes de corte nas bordas.

    Para celulas de borda com corte, o talude se estende para fora.
    Volume prisma triangular = 0.5 * h^2 * (H/V) * comprimento_segmento.

    Args:
        borda: Mascara de celulas de borda ja calculada (opcional, evita
            recalcular quando o chamador processa corte e aterro juntos).

    Returns:
        Volume adicional de corte em m3.
    """
    if borda is None:
        borda = identificar_celulas_borda(grade)
    elevacoes = superficie.elevacao_grade
    esp = grade.espacamento

    terreno_ajustado = elevacoes - remocao_vegetal
    delta = cota_projeto - terreno_ajustado

    # Apenas bordas com corte (delta < 0)
    mascara = borda & (delta < 0) & ~np.isnan(elevacoes)
    alturas_corte = np.abs(delta[mascara])

    if len(alturas_corte) == 0:
        return 0.0

    # Volume do talude: prisma triangular por segmento de borda
    razao = inclinacao_h / inclinacao_v
    volume = float(np.sum(0.5 * alturas_corte ** 2 * razao * esp))

    return volume


def calcular_volume_talude_aterro(
    grade: GradePoligono,
    superficie: SuperficieTerreno,
    cota_projeto: float,
    inclinacao_h: float = 2.0,
    inclinacao_v: float = 1.0,
    remocao_vegetal: float = 0.30,
    borda: np.ndarray = None,
) -> float:
    """Calcula volume adicional dos taludes de aterro nas bordas.

    Similar ao corte, mas com inclinacao de aterro.

    Returns:
        Volume adicional de aterro em m3.
    """
    if borda is None:
        borda = identificar_celulas_borda(grade)
    elevacoes = superficie.elevacao_grade
    esp = grade.espacamento

    terreno_ajustado = elevacoes - remocao_vegetal
    delta = cota_projeto - terreno_ajustado

    # Apenas bordas com aterro (delta > 0)
    mascara = borda & (delta > 0) & ~np.isnan(elevacoes)
    alturas_aterro = delta[mascara]

    if len(alturas_aterro) == 0:
        return 0.0

    razao = inclinacao_h / inclinacao_v
    volume = float(np.sum(0.5 * alturas_aterro ** 2 * razao * esp))

    return volume


