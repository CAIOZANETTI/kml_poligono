"""Modelo de greide de projeto: plato plano + taludes com daylight por inclinacao local.

Abordagem B: o talude sai da aresta do plato (na cota de projeto) e morre no
terreno natural extrapolado pela inclinacao local de cada estacao da divisa.
Isso captura o talude "crescendo morro acima/abaixo" e da o footprint real
(o quanto a terraplenagem invade alem da divisa) e o volume escondido nos
proprios taludes.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.interpolate import griddata
from shapely.geometry import Polygon

from modulos.geometria import GradePoligono
from modulos.terreno import SuperficieTerreno

_TOL = 1e-3        # m, tolerancia para classificar corte/aterro
_RUN_MAX_FAT = 4.0  # multiplicador do run maximo antes de clampar


@dataclass
class ContornoGreide:
    """Estacoes ao longo da divisa, independentes da cota de projeto."""
    pts: np.ndarray        # (n, 2) pontos da divisa densificada
    normal: np.ndarray     # (n, 2) normal externa unitaria
    z_borda: np.ndarray    # (n,) cota do terreno natural na divisa
    g: np.ndarray          # (n,) inclinacao local do terreno (d_elev/d_dist externa)
    seg_len: np.ndarray    # (n,) comprimento de divisa atribuido a cada estacao
    area_lote: float       # m2


@dataclass
class TaludesResolvidos:
    """Resultado da resolucao dos taludes para uma cota especifica."""
    cota: float
    inner: np.ndarray          # (n, 3) aresta do plato (na cota)
    outer: np.ndarray          # (n, 3) linha de daylight (no terreno)
    run: np.ndarray            # (n,) extensao horizontal do talude
    dh: np.ndarray             # (n,) z_borda - cota (>0 corte, <0 aterro)
    is_corte: np.ndarray       # (n,) bool
    is_aterro: np.ndarray      # (n,) bool
    incompleto: np.ndarray     # (n,) bool - talude nao encontrou o terreno (clampado)
    volume_corte: float        # m3 nos taludes de corte
    volume_aterro: float       # m3 nos taludes de aterro
    area_footprint: float      # m2 invadidos alem da divisa
    poligono_offset: np.ndarray  # (n, 2) anel de daylight


def amostrar_contorno(
    grade: GradePoligono,
    superficie: SuperficieTerreno,
    remocao_vegetal: float = 0.0,
) -> ContornoGreide:
    """Densifica a divisa e calcula normal externa, cota e inclinacao local.

    Independe da cota de projeto, entao pode ser reaproveitado numa varredura.
    """
    poly = grade.poligono_shapely
    ext = poly.exterior
    comprimento = ext.length
    n = max(12, int(np.ceil(comprimento / grade.espacamento)))
    dists = np.linspace(0.0, comprimento, n, endpoint=False)
    pts = np.array([ext.interpolate(float(t)).coords[0] for t in dists])

    # Normal externa: gira a tangente e orienta para fora do centroide
    nxt = np.roll(pts, -1, axis=0)
    prv = np.roll(pts, 1, axis=0)
    tang = nxt - prv
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
    normal = np.column_stack([tang[:, 1], -tang[:, 0]])
    centro = np.array(poly.centroid.coords[0])
    sinal = np.sign(np.sum((pts - centro) * normal, axis=1))
    sinal[sinal == 0] = 1.0
    normal *= sinal[:, None]

    # Amostra o terreno interpolado em duas estacoes para dentro
    esp = grade.espacamento
    pa = pts - normal * esp          # 1 espacamento para dentro
    pb = pts - normal * 2.0 * esp    # 2 espacamentos para dentro
    xy = superficie.pontos_grade_xy
    zg = superficie.elevacao_grade
    za = griddata(xy, zg, pa, method="linear")
    zb = griddata(xy, zg, pb, method="linear")
    # Fallback nearest onde a malha nao cobre
    for arr, p in ((za, pa), (zb, pb)):
        m = np.isnan(arr)
        if m.any():
            arr[m] = griddata(xy, zg, p[m], method="nearest")

    g = (za - zb) / esp                  # variacao por metro indo para fora
    z_borda = za + g * esp - remocao_vegetal  # extrapola ate a divisa (s=0)

    # Comprimento de divisa atribuido a cada estacao (ponto medio dos vizinhos)
    seg_len = np.full(n, comprimento / n)

    return ContornoGreide(
        pts=pts, normal=normal, z_borda=z_borda, g=g,
        seg_len=seg_len, area_lote=float(poly.area),
    )


def resolver_taludes(
    contorno: ContornoGreide,
    cota: float,
    razao_corte: float = 1.0,
    razao_aterro: float = 2.0,
) -> TaludesResolvidos:
    """Resolve o daylight de cada estacao para uma cota dada (abordagem B).

    Corte:  cota + s/razao_corte  = z_borda + g*s  ->  s = dh / (1/razao_corte - g)
    Aterro: cota - s/razao_aterro = z_borda + g*s  ->  s = -dh / (g + 1/razao_aterro)
    """
    pts, normal = contorno.pts, contorno.normal
    z_borda, g = contorno.z_borda, contorno.g
    n = len(pts)

    dh = z_borda - cota
    is_corte = dh > _TOL
    is_aterro = dh < -_TOL

    run = np.zeros(n)
    incompleto = np.zeros(n, dtype=bool)

    run_max = _RUN_MAX_FAT * (np.max(np.abs(dh)) if n else 0.0) \
        * max(razao_corte, razao_aterro) + 1e-6

    den_c = 1.0 / razao_corte - g
    den_a = g + 1.0 / razao_aterro

    with np.errstate(divide="ignore", invalid="ignore"):
        s_c = np.where(den_c > 1e-9, dh / den_c, np.inf)
        s_a = np.where(den_a > 1e-9, -dh / den_a, np.inf)

    run[is_corte] = s_c[is_corte]
    run[is_aterro] = s_a[is_aterro]

    # Talude mais raso que o terreno -> nao encontra: clampa e sinaliza
    ruim = ~np.isfinite(run) | (run < 0) | (run > run_max)
    incompleto = ruim & (is_corte | is_aterro)
    run = np.where(ruim, run_max, run)
    run[~(is_corte | is_aterro)] = 0.0

    inner = np.column_stack([pts[:, 0], pts[:, 1], np.full(n, float(cota))])
    z_out = z_borda + g * run
    outer = np.column_stack([pts[:, 0] + normal[:, 0] * run,
                             pts[:, 1] + normal[:, 1] * run, z_out])

    # Volume da cunha triangular por estacao: 0.5 * |dh| * run * comprimento
    vol = 0.5 * np.abs(dh) * run * contorno.seg_len
    volume_corte = float(np.sum(vol[is_corte]))
    volume_aterro = float(np.sum(vol[is_aterro]))

    offset_xy = outer[:, :2]
    try:
        area_off = Polygon(offset_xy).area
    except Exception:
        area_off = contorno.area_lote
    area_footprint = float(max(0.0, area_off - contorno.area_lote))

    return TaludesResolvidos(
        cota=float(cota), inner=inner, outer=outer, run=run, dh=dh,
        is_corte=is_corte, is_aterro=is_aterro, incompleto=incompleto,
        volume_corte=volume_corte, volume_aterro=volume_aterro,
        area_footprint=area_footprint, poligono_offset=offset_xy,
    )


def volumes_internos(
    superficie: SuperficieTerreno,
    cota: float,
    espacamento: float,
    remocao_vegetal: float = 0.0,
) -> tuple:
    """Volume de corte/aterro DENTRO do lote (entre terreno e plato plano).

    Returns:
        (volume_corte, volume_aterro) em m3.
    """
    elev = superficie.elevacao_grade - remocao_vegetal
    valido = ~np.isnan(elev)
    delta = elev[valido] - cota          # >0 corte, <0 aterro
    area = espacamento ** 2
    corte = float(np.sum(delta[delta > 0]) * area)
    aterro = float(np.sum(-delta[delta < 0]) * area)
    return corte, aterro


def varredura_cota(
    contorno: ContornoGreide,
    superficie: SuperficieTerreno,
    espacamento: float,
    cotas: np.ndarray,
    razao_corte: float = 1.0,
    razao_aterro: float = 2.0,
    remocao_vegetal: float = 0.0,
) -> dict:
    """Varre a cota de projeto somando terraplenagem interna + taludes.

    Returns dict com arrays: cotas, corte_total, aterro_total, footprint,
    e a cota de menor volume total movimentado e a de equilibrio corte=aterro.
    """
    corte_tot, aterro_tot, foot = [], [], []
    for c in cotas:
        ci, ai = volumes_internos(superficie, float(c), espacamento, remocao_vegetal)
        tal = resolver_taludes(contorno, float(c), razao_corte, razao_aterro)
        corte_tot.append(ci + tal.volume_corte)
        aterro_tot.append(ai + tal.volume_aterro)
        foot.append(tal.area_footprint)

    corte_tot = np.array(corte_tot)
    aterro_tot = np.array(aterro_tot)
    foot = np.array(foot)
    total = corte_tot + aterro_tot

    cota_min_total = float(cotas[int(np.argmin(total))])
    # Equilibrio: onde |corte - aterro| e minimo
    cota_equilibrio = float(cotas[int(np.argmin(np.abs(corte_tot - aterro_tot)))])

    return {
        "cotas": cotas,
        "corte_total": corte_tot,
        "aterro_total": aterro_tot,
        "footprint": foot,
        "total": total,
        "cota_min_total": cota_min_total,
        "cota_equilibrio": cota_equilibrio,
    }
