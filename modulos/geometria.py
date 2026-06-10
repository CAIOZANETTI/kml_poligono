"""Operacoes geometricas: conversao UTM, geracao de grade, operacoes poligonais."""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from shapely.geometry import Polygon
import shapely
import utm as utm_lib

from modulos.leitor_kml import PoligonoKML, PontoKML


@dataclass
class PontoUTM:
    """Ponto em coordenadas UTM (metros)."""
    easting: float
    northing: float
    elevacao: float
    zona_utm: int = 0
    letra_utm: str = ""


@dataclass
class GradePoligono:
    """Grade de pontos internos de um poligono processado."""
    nome: str
    pontos_borda: np.ndarray       # shape (N, 3) - easting, northing, elevacao
    pontos_grade: np.ndarray       # shape (M, 2) - easting, northing
    poligono_shapely: Polygon
    zona_utm: int
    letra_utm: str
    espacamento: float
    area: float                    # m2
    perimetro: float               # m


def converter_para_utm(pontos: List[PontoKML]) -> Tuple[List[PontoUTM], int, str]:
    """Converte lista de pontos lat/lon para coordenadas UTM.

    Usa a zona UTM do centroide para garantir consistencia.

    Returns:
        (pontos_utm, zona_numero, zona_letra)
    """
    # Calcula centroide para determinar zona UTM
    lat_media = np.mean([p.latitude for p in pontos])
    lon_media = np.mean([p.longitude for p in pontos])
    _, _, zona_num, zona_letra = utm_lib.from_latlon(lat_media, lon_media)

    pontos_utm = []
    for p in pontos:
        easting, northing, _, _ = utm_lib.from_latlon(
            p.latitude, p.longitude,
            force_zone_number=zona_num,
            force_zone_letter=zona_letra,
        )
        elev = p.elevacao if p.elevacao is not None else 0.0
        pontos_utm.append(PontoUTM(
            easting=easting,
            northing=northing,
            elevacao=elev,
            zona_utm=zona_num,
            letra_utm=zona_letra,
        ))

    return pontos_utm, zona_num, zona_letra


def criar_poligono_shapely(pontos_utm: List[PontoUTM]) -> Polygon:
    """Cria poligono Shapely 2D a partir dos pontos UTM."""
    coords = [(p.easting, p.northing) for p in pontos_utm]
    return Polygon(coords)


def gerar_grade_interna(
    poligono: Polygon,
    espacamento: float = 1.0,
) -> np.ndarray:
    """Gera grade regular de pontos internos ao poligono.

    Cria meshgrid sobre o bounding box e filtra pontos dentro do poligono.

    Args:
        poligono: Poligono Shapely.
        espacamento: Distancia entre pontos em metros.

    Returns:
        np.ndarray shape (M, 2) com easting/northing dos pontos internos.

    Raises:
        ValueError: Se a combinacao area x espacamento gerar uma grade
            grande demais para processar com seguranca.
    """
    minx, miny, maxx, maxy = poligono.bounds

    # Guarda de memoria: grades com milhoes de pontos travam a aplicacao
    n_estimado = ((maxx - minx) / espacamento + 1) * ((maxy - miny) / espacamento + 1)
    if n_estimado > 4_000_000:
        raise ValueError(
            "Grade de ~{:,.0f} pontos excede o limite de 4 milhoes. "
            "Aumente o espacamento da grade (atual: {} m).".format(
                n_estimado, espacamento,
            )
        )

    # Cria grade regular
    xs = np.arange(minx, maxx + espacamento, espacamento)
    ys = np.arange(miny, maxy + espacamento, espacamento)
    grade_x, grade_y = np.meshgrid(xs, ys)
    pontos_x = grade_x.ravel()
    pontos_y = grade_y.ravel()

    # Filtra pontos dentro do poligono usando shapely vetorizado
    from shapely import contains_xy
    mascara = contains_xy(poligono, pontos_x, pontos_y)

    pontos_internos = np.column_stack([
        pontos_x[mascara],
        pontos_y[mascara],
    ])

    return pontos_internos


def processar_poligono(
    poligono_kml: PoligonoKML,
    espacamento: float = 1.0,
) -> GradePoligono:
    """Pipeline completo: KML -> UTM -> Shapely -> Grade interna.

    Args:
        poligono_kml: Poligono extraido do KML.
        espacamento: Espacamento da grade em metros.

    Returns:
        GradePoligono pronto para interpolacao de terreno.
    """
    # Converte para UTM
    pontos_utm, zona, letra = converter_para_utm(poligono_kml.pontos)

    # Cria poligono Shapely
    poly = criar_poligono_shapely(pontos_utm)
    if not poly.is_valid:
        raise ValueError(
            "Poligono '{}' e invalido (provavel auto-intersecao no desenho). "
            "Corrija o tracado no Google Earth e reimporte o KML.".format(
                poligono_kml.nome,
            )
        )

    # Array de pontos da borda com elevacao
    pontos_borda = np.array([
        [p.easting, p.northing, p.elevacao]
        for p in pontos_utm
    ])

    # Gera grade interna
    pontos_grade = gerar_grade_interna(poly, espacamento)

    return GradePoligono(
        nome=poligono_kml.nome,
        pontos_borda=pontos_borda,
        pontos_grade=pontos_grade,
        poligono_shapely=poly,
        zona_utm=zona,
        letra_utm=letra,
        espacamento=espacamento,
        area=calcular_area_poligono(poly),
        perimetro=calcular_perimetro(poly),
    )


def utm_para_latlon(
    pontos_xy: np.ndarray,
    zona: int,
    letra: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """Converte pontos UTM (easting, northing) de volta para lat/lon.

    Args:
        pontos_xy: Array (M, 2) com easting/northing.
        zona: Numero da zona UTM.
        letra: Letra da zona UTM.

    Returns:
        (latitudes, longitudes) como arrays float.
    """
    n = len(pontos_xy)
    if n == 0:
        return np.empty(0), np.empty(0)

    # Caminho vetorizado: a lib utm aceita arrays NumPy diretamente
    try:
        lats, lons = utm_lib.to_latlon(
            np.ascontiguousarray(pontos_xy[:, 0], dtype=float),
            np.ascontiguousarray(pontos_xy[:, 1], dtype=float),
            zona, letra,
        )
        return np.asarray(lats, dtype=float), np.asarray(lons, dtype=float)
    except Exception:
        pass

    # Fallback ponto a ponto
    lats = np.empty(n)
    lons = np.empty(n)
    for i in range(n):
        lat, lon = utm_lib.to_latlon(
            float(pontos_xy[i, 0]), float(pontos_xy[i, 1]), zona, letra,
        )
        lats[i] = lat
        lons[i] = lon
    return lats, lons


def calcular_area_poligono(poligono: Polygon) -> float:
    """Calcula area do poligono em metros quadrados."""
    return poligono.area


def calcular_perimetro(poligono: Polygon) -> float:
    """Calcula perimetro do poligono em metros."""
    return poligono.length
