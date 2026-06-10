"""Testes de regressao do pipeline de terraplenagem.

Rodar com: python -m pytest tests/ -q
Os testes marcados com 'rede' dependem de acesso a internet (DEM/APIs).
"""

import math

import numpy as np
import pytest

from modulos.leitor_kml import ler_arquivo_kml, PoligonoKML, PontoKML
from modulos.geometria import processar_poligono, utm_para_latlon
from modulos.terreno import interpolar_terreno
from modulos.volumes import calcular_volumes, calcular_cota_otima
from modulos import elevacao as mod_elevacao
from modulos.elevacao import completar_elevacao_poligono


# ─── Helpers ───

def _poligono_circular(n=12, raio_graus=0.003, elev_base=750.0, sem_elev=()):
    """Poligono aproximadamente circular com elevacao senoidal."""
    pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n
        pts.append(PontoKML(
            longitude=-46.65 + raio_graus * math.cos(ang),
            latitude=-23.55 + raio_graus * math.sin(ang),
            elevacao=None if i in sem_elev else elev_base + 5 * math.sin(ang),
        ))
    return PoligonoKML(nome="teste", pontos=pts, tem_elevacao=True)


# ─── Leitor KML ───

def test_exemplo_dois_poligonos():
    with open("exemplos/exemplo_poligono.kml", "rb") as f:
        polys = ler_arquivo_kml(f.read(), "exemplo.kml")
    assert len(polys) == 2
    assert all(p.tem_elevacao for p in polys)


def test_exemplo_lg_dois_poligonos_sem_elevacao():
    """Exemplo pre-carregado da Home: 2 poligonos, elevacao vem do DEM."""
    with open("exemplos/LG.kml", "rb") as f:
        polys = ler_arquivo_kml(f.read(), "LG.kml")
    assert len(polys) == 2
    assert {p.nome for p in polys} == {"fabrica", "canteiro"}
    assert all(not p.tem_elevacao for p in polys)


def test_multigeometry_nao_duplica():
    kml = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark>
  <name>Gleba</name>
  <MultiGeometry>
    <Polygon><outerBoundaryIs><LinearRing><coordinates>
      -46.65,-23.55,750 -46.64,-23.55,752 -46.64,-23.54,755 -46.65,-23.54,753 -46.65,-23.55,750
    </coordinates></LinearRing></outerBoundaryIs></Polygon>
    <Polygon><outerBoundaryIs><LinearRing><coordinates>
      -46.63,-23.55,760 -46.62,-23.55,762 -46.62,-23.54,765 -46.63,-23.54,763 -46.63,-23.55,760
    </coordinates></LinearRing></outerBoundaryIs></Polygon>
  </MultiGeometry>
</Placemark></Document></kml>"""
    polys = ler_arquivo_kml(kml, "multi.kml")
    assert len(polys) == 2


# ─── Elevacao ───

def test_elevacao_ausente_preenchida_por_vizinho(monkeypatch):
    """Pontos None (<=10%) nao podem virar cota 0; herdam o vizinho."""
    poly = _poligono_circular(n=12, sem_elev=(5,))
    poly.tem_elevacao = False
    monkeypatch.setattr(
        mod_elevacao, "obter_elevacao", lambda pontos, **kw: [None] * len(pontos),
    )
    completo = completar_elevacao_poligono(poly)
    elevs = [p.elevacao for p in completo.pontos]
    assert all(e is not None for e in elevs)
    assert min(elevs) > 700  # nada despencou para 0


def test_elevacao_toda_ausente_levanta_erro(monkeypatch):
    poly = _poligono_circular(n=12, sem_elev=tuple(range(12)))
    poly.tem_elevacao = False
    monkeypatch.setattr(
        mod_elevacao, "obter_elevacao", lambda pontos, **kw: [None] * len(pontos),
    )
    with pytest.raises(ValueError):
        completar_elevacao_poligono(poly)


def test_interpolacao_sem_contaminacao():
    """Superficie interpolada fica dentro da faixa de elevacao da borda."""
    poly = _poligono_circular()
    grade = processar_poligono(poly, espacamento=20.0)
    sup = interpolar_terreno(grade)
    assert 740 < sup.elevacao_min and sup.elevacao_max < 760


def test_interpolacao_com_elevacao_de_grade_conhecida():
    poly = _poligono_circular()
    grade = processar_poligono(poly, espacamento=20.0)
    conhecida = np.full(len(grade.pontos_grade), 800.0)
    conhecida[0] = np.nan  # um faltante a preencher
    sup = interpolar_terreno(grade, elevacao_grade_conhecida=conhecida)
    assert abs(sup.elevacao_media - 800.0) < 5.0
    assert not np.isnan(sup.elevacao_grade).any()


# ─── Geometria ───

def test_poligono_invalido_rejeitado():
    pts = [PontoKML(-46.650, -23.550, 750), PontoKML(-46.645, -23.545, 755),
           PontoKML(-46.650, -23.545, 752), PontoKML(-46.645, -23.550, 753)]
    poly = PoligonoKML("bowtie", pts, tem_elevacao=True)
    with pytest.raises(ValueError, match="invalido"):
        processar_poligono(poly, espacamento=10.0)


def test_grade_grande_demais_rejeitada():
    poly = _poligono_circular(raio_graus=0.05)  # ~11 km de diametro
    with pytest.raises(ValueError, match="limite"):
        processar_poligono(poly, espacamento=0.5)


def test_utm_para_latlon_roundtrip():
    poly = _poligono_circular()
    grade = processar_poligono(poly, espacamento=20.0)
    lats, lons = utm_para_latlon(grade.pontos_grade, grade.zona_utm, grade.letra_utm)
    assert np.all(np.abs(lats + 23.55) < 0.01)
    assert np.all(np.abs(lons + 46.65) < 0.01)


# ─── Volumes ───

def test_cota_otima_inclui_taludes():
    poly = _poligono_circular()
    grade = processar_poligono(poly, espacamento=20.0)
    sup = interpolar_terreno(grade)
    cota, res = calcular_cota_otima(
        sup, 20.0, 0.30, nome_poligono="t",
        talude_corte_h=1.0, talude_corte_v=1.0,
        talude_aterro_h=2.0, talude_aterro_v=1.0, grade=grade,
    )
    # Resultado final carrega os volumes de talude
    assert res.volume_talude_corte > 0 or res.volume_talude_aterro > 0
    # Balanco geometrico (com taludes) proximo de zero na cota otima
    assert abs(res.balanco_massa) < max(0.01 * res.volume_corte, 5.0)


def test_volumes_consistentes_com_cota_media():
    poly = _poligono_circular()
    grade = processar_poligono(poly, espacamento=20.0)
    sup = interpolar_terreno(grade)
    res = calcular_volumes(
        sup, sup.elevacao_media, 20.0, 0.30, "t",
        grade=grade,
    )
    assert res.volume_corte > 0
    assert res.volume_aterro > 0
    assert res.area_total > 0
    # Balanco geometrico coerente
    assert abs(res.balanco_massa - (res.volume_corte - res.volume_aterro)) < 1e-6


# ─── Rede (DEM) ───

@pytest.mark.rede
def test_amostragem_dem_grade():
    """Grade interna amostrada direto do tile Copernicus (precisa de rede)."""
    lats = np.array([-25.65, -25.651, -25.652])
    lons = np.array([-49.30, -49.301, -49.302])
    elevs = mod_elevacao.obter_elevacao_grade_dem(lats, lons)
    if np.all(np.isnan(elevs)):
        pytest.skip("DEM indisponivel (sem rede)")
    assert np.nanmin(elevs) > 500 and np.nanmax(elevs) < 1500
