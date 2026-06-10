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
    elevacao_grade_conhecida: np.ndarray = None,
) -> SuperficieTerreno:
    """Interpola elevacao do terreno nos pontos da grade interna.

    Quando ``elevacao_grade_conhecida`` e fornecida (amostragem direta do DEM
    nos pontos internos), ela e usada como fonte primaria — o relevo interno
    real e capturado. Pontos NaN remanescentes sao preenchidos por
    interpolacao a partir da borda e dos pontos validos.

    Sem ela (caso de KML com elevacao propria, ex. levantamento RTK apenas
    nos vertices), usa scipy.griddata com as elevacoes da borda.

    Args:
        grade: GradePoligono com borda e grade interna.
        metodo: Metodo de interpolacao ('linear', 'cubic', 'nearest').
        elevacao_grade_conhecida: Array (M,) com elevacoes ja amostradas
            nos pontos da grade (NaN onde indisponivel), ou None.

    Returns:
        SuperficieTerreno com elevacoes interpoladas.
    """
    # Pontos conhecidos: vertices da borda
    pontos_conhecidos = grade.pontos_borda[:, :2]  # (N, 2)
    valores_conhecidos = grade.pontos_borda[:, 2]   # (N,)

    # Pontos onde interpolar: grade interna
    pontos_grade = grade.pontos_grade  # (M, 2)

    if elevacao_grade_conhecida is not None and len(pontos_grade) > 0:
        elevacao_grade = np.asarray(elevacao_grade_conhecida, dtype=float).copy()
        mascara_nan = np.isnan(elevacao_grade)
        if mascara_nan.any():
            # Preenche faltantes com borda + pontos de grade validos
            pts = np.vstack([pontos_conhecidos, pontos_grade[~mascara_nan]])
            vals = np.concatenate([valores_conhecidos, elevacao_grade[~mascara_nan]])
            preenchido = griddata(pts, vals, pontos_grade[mascara_nan], method="linear")
            ainda_nan = np.isnan(preenchido)
            if ainda_nan.any():
                preenchido[ainda_nan] = griddata(
                    pts, vals, pontos_grade[mascara_nan][ainda_nan], method="nearest",
                )
            elevacao_grade[mascara_nan] = preenchido
    else:
        # Interpolacao a partir da borda
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
