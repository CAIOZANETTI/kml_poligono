"""Calculo de taludes de corte e aterro nas bordas do poligono."""

from typing import Tuple

import numpy as np
from shapely.geometry import Polygon

from modulos.geometria import GradePoligono
from modulos.terreno import SuperficieTerreno


def identificar_celulas_borda(grade: GradePoligono) -> np.ndarray:
    """Identifica pontos da grade que estao na borda do poligono.

    Um ponto e de borda se algum vizinho (4-conectividade) esta
    fora do poligono ou nao existe na grade.

    Returns:
        Array booleano (M,) marcando celulas de borda.
    """
    pontos = grade.pontos_grade
    esp = grade.espacamento

    # Cria set de pontos para busca rapida (arredondado)
    precisao = esp / 10.0
    pontos_set = set()
    for i in range(len(pontos)):
        chave = (
            round(pontos[i, 0] / precisao) * precisao,
            round(pontos[i, 1] / precisao) * precisao,
        )
        pontos_set.add(chave)

    borda = np.zeros(len(pontos), dtype=bool)
    deslocamentos = [(esp, 0), (-esp, 0), (0, esp), (0, -esp)]

    for i in range(len(pontos)):
        x, y = pontos[i, 0], pontos[i, 1]
        for dx, dy in deslocamentos:
            vizinho = (
                round((x + dx) / precisao) * precisao,
                round((y + dy) / precisao) * precisao,
            )
            if vizinho not in pontos_set:
                borda[i] = True
                break

    return borda


def calcular_volume_talude_corte(
    grade: GradePoligono,
    superficie: SuperficieTerreno,
    cota_projeto: float,
    inclinacao_h: float = 1.0,
    inclinacao_v: float = 1.0,
    remocao_vegetal: float = 0.30,
) -> float:
    """Calcula volume adicional dos taludes de corte nas bordas.

    Para celulas de borda com corte, o talude se estende para fora.
    Volume prisma triangular = 0.5 * h^2 * (H/V) * comprimento_segmento.

    Returns:
        Volume adicional de corte em m3.
    """
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
) -> float:
    """Calcula volume adicional dos taludes de aterro nas bordas.

    Similar ao corte, mas com inclinacao de aterro.

    Returns:
        Volume adicional de aterro em m3.
    """
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


def calcular_extensao_talude(
    altura: float,
    inclinacao_h: float,
    inclinacao_v: float,
) -> float:
    """Calcula extensao horizontal de um talude.

    extensao = altura * (H / V)
    """
    return altura * (inclinacao_h / inclinacao_v)


def gerar_perfil_talude(
    altura: float,
    inclinacao_h: float,
    inclinacao_v: float,
    num_pontos: int = 50,
) -> Tuple[np.ndarray, np.ndarray]:
    """Gera coordenadas x, y do perfil de um talude para visualizacao.

    Returns:
        (x_perfil, y_perfil) arrays com coordenadas do talude.
    """
    extensao = calcular_extensao_talude(altura, inclinacao_h, inclinacao_v)
    x = np.linspace(0, extensao, num_pontos)
    y = x * (inclinacao_v / inclinacao_h)
    return x, y
