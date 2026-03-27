"""Interpolacao de terreno e geracao de superficies."""

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy.interpolate import griddata

from modulos.geometria import GradePoligono


@dataclass
class SuperficieTerreno:
    """Superficie interpolada do terreno natural."""
    grade_x: np.ndarray          # 1D array de coordenadas X unicas
    grade_y: np.ndarray          # 1D array de coordenadas Y unicas
    malha_x: np.ndarray          # 2D meshgrid X
    malha_y: np.ndarray          # 2D meshgrid Y
    elevacao_grade: np.ndarray   # 1D array, elevacao em cada ponto da grade
    elevacao_malha: np.ndarray   # 2D array para surface plot (NaN fora do poligono)
    elevacao_min: float
    elevacao_max: float
    elevacao_media: float
    pontos_grade_xy: np.ndarray  # shape (M, 2) - coordenadas dos pontos da grade


def interpolar_terreno(
    grade: GradePoligono,
    metodo: str = "cubic",
) -> SuperficieTerreno:
    """Interpola elevacao do terreno nos pontos da grade interna.

    Usa scipy.griddata com elevacoes dos vertices da borda como pontos conhecidos.

    Args:
        grade: GradePoligono com borda e grade interna.
        metodo: Metodo de interpolacao ('linear', 'cubic', 'nearest').

    Returns:
        SuperficieTerreno com elevacoes interpoladas.
    """
    # Pontos conhecidos: vertices da borda
    pontos_conhecidos = grade.pontos_borda[:, :2]  # (N, 2)
    valores_conhecidos = grade.pontos_borda[:, 2]   # (N,)

    # Pontos onde interpolar: grade interna
    pontos_grade = grade.pontos_grade  # (M, 2)

    # Interpolacao
    elevacao_grade = griddata(
        pontos_conhecidos,
        valores_conhecidos,
        pontos_grade,
        method=metodo,
    )

    # Fallback para nearest onde cubic/linear falha (NaN nas bordas)
    mascara_nan = np.isnan(elevacao_grade)
    if mascara_nan.any():
        elevacao_nearest = griddata(
            pontos_conhecidos,
            valores_conhecidos,
            pontos_grade[mascara_nan],
            method="nearest",
        )
        elevacao_grade[mascara_nan] = elevacao_nearest

    # Cria malha 2D para visualizacao
    malha_x, malha_y, elevacao_malha = criar_malha_2d(grade, elevacao_grade)

    elev_validos = elevacao_grade[~np.isnan(elevacao_grade)]

    return SuperficieTerreno(
        grade_x=np.unique(pontos_grade[:, 0]),
        grade_y=np.unique(pontos_grade[:, 1]),
        malha_x=malha_x,
        malha_y=malha_y,
        elevacao_grade=elevacao_grade,
        elevacao_malha=elevacao_malha,
        elevacao_min=float(np.nanmin(elev_validos)) if len(elev_validos) > 0 else 0.0,
        elevacao_max=float(np.nanmax(elev_validos)) if len(elev_validos) > 0 else 0.0,
        elevacao_media=float(np.nanmean(elev_validos)) if len(elev_validos) > 0 else 0.0,
        pontos_grade_xy=pontos_grade,
    )


def calcular_diferenca_terreno(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    remocao_vegetal: float = 0.30,
) -> np.ndarray:
    """Calcula diferenca entre cota de projeto e terreno ajustado.

    delta = cota_projeto - (elevacao_terreno - remocao_vegetal)
    Positivo = aterro, negativo = corte.

    Returns:
        1D array de deltas em cada ponto da grade.
    """
    terreno_ajustado = superficie.elevacao_grade - remocao_vegetal
    return cota_projeto - terreno_ajustado


def gerar_superficie_projeto(
    superficie: SuperficieTerreno,
    cota_projeto: float,
) -> np.ndarray:
    """Gera superficie plana do projeto na cota especificada.

    Returns:
        2D array com a cota do projeto (NaN fora do poligono).
    """
    projeto = np.full_like(superficie.elevacao_malha, np.nan)
    mascara = ~np.isnan(superficie.elevacao_malha)
    projeto[mascara] = cota_projeto
    return projeto


def criar_malha_2d(
    grade: GradePoligono,
    valores: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reorganiza valores 1D da grade para malha 2D.

    Pontos fora do poligono ficam como NaN.

    Returns:
        (malha_x, malha_y, malha_valores) todos arrays 2D.
    """
    pontos = grade.pontos_grade

    # Coordenadas unicas
    xs = np.unique(pontos[:, 0])
    ys = np.unique(pontos[:, 1])

    malha_x, malha_y = np.meshgrid(xs, ys)
    malha_vals = np.full(malha_x.shape, np.nan)

    # Mapeia pontos para indices via numpy searchsorted (vetorizado)
    xi = np.searchsorted(xs, pontos[:, 0])
    yi = np.searchsorted(ys, pontos[:, 1])

    # Valida que indices estao dentro dos limites
    mascara = (xi < len(xs)) & (yi < len(ys))
    malha_vals[yi[mascara], xi[mascara]] = valores[mascara]

    return malha_x, malha_y, malha_vals
