"""Calculo de volumes de corte e aterro pelo metodo de grade.

Referencia: DNIT 106/2009-ES (Cortes), DNIT 108/2009-ES (Aterros).
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict

import numpy as np

from modulos.terreno import SuperficieTerreno
from modulos.parametros import (
    CategoriaSolo,
    obter_fator_empolamento,
    obter_fator_homogeneizacao,
)


@dataclass
class ResultadoVolume:
    """Resultado do calculo de volumes para um poligono."""
    nome_poligono: str
    cota_projeto: float
    area_total: float                # m2
    volume_corte_bruto: float        # m3 (in-situ)
    volume_aterro_bruto: float       # m3 (in-situ)
    volume_corte_empolado: float     # m3 (apos empolamento)
    volume_aterro_compactado: float  # m3 (apos homogeneizacao)
    volume_bota_fora: float          # m3 (excesso de corte)
    volume_solo_importado: float     # m3 (deficit)
    balanco_massa: float             # m3 (corte_empolado - aterro_compactado)
    area_corte: float                # m2
    area_aterro: float               # m2
    elevacao_media_terreno: float
    remocao_vegetal: float
    categoria_solo: CategoriaSolo


def calcular_volumes(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    espacamento: float,
    remocao_vegetal: float = 0.30,
    categoria: CategoriaSolo = CategoriaSolo.PRIMEIRA,
    nome_poligono: str = "",
) -> ResultadoVolume:
    """Calcula volumes de corte e aterro pelo metodo de grade.

    Metodo: cada celula tem area = espacamento^2.
    delta = cota_projeto - (elevacao - remocao_vegetal)
    Positivo = aterro, negativo = corte.

    Fatores DNIT aplicados:
        volume_corte_empolado = corte_bruto * empolamento
        volume_aterro_compactado = aterro_bruto * homogeneizacao
        balanco = corte_empolado - aterro_compactado

    Args:
        superficie: Terreno interpolado.
        cota_projeto: Cota de projeto (m).
        espacamento: Espacamento da grade (m).
        remocao_vegetal: Camada vegetal removida (m).
        categoria: Categoria de solo DNIT.
        nome_poligono: Nome para referencia.

    Returns:
        ResultadoVolume com todos os volumes calculados.
    """
    area_celula = espacamento ** 2
    elevacoes = superficie.elevacao_grade

    # Filtra NaN
    mascara_valida = ~np.isnan(elevacoes)
    elev_validas = elevacoes[mascara_valida]

    # Delta: positivo = aterro, negativo = corte
    terreno_ajustado = elev_validas - remocao_vegetal
    delta = cota_projeto - terreno_ajustado

    # Separar corte e aterro
    mascara_corte = delta < 0
    mascara_aterro = delta > 0

    vol_corte_bruto = float(np.sum(np.abs(delta[mascara_corte])) * area_celula)
    vol_aterro_bruto = float(np.sum(delta[mascara_aterro]) * area_celula)

    area_corte = float(np.sum(mascara_corte) * area_celula)
    area_aterro = float(np.sum(mascara_aterro) * area_celula)

    # Aplica fatores DNIT
    fator_emp = obter_fator_empolamento(categoria)
    fator_hom = obter_fator_homogeneizacao(categoria)

    vol_corte_empolado = vol_corte_bruto * fator_emp
    vol_aterro_compactado = vol_aterro_bruto * fator_hom

    # Balanco de massa
    balanco = vol_corte_empolado - vol_aterro_compactado
    vol_bota_fora = max(0.0, balanco)
    vol_solo_importado = max(0.0, -balanco)

    return ResultadoVolume(
        nome_poligono=nome_poligono,
        cota_projeto=cota_projeto,
        area_total=float(np.sum(mascara_valida) * area_celula),
        volume_corte_bruto=vol_corte_bruto,
        volume_aterro_bruto=vol_aterro_bruto,
        volume_corte_empolado=vol_corte_empolado,
        volume_aterro_compactado=vol_aterro_compactado,
        volume_bota_fora=vol_bota_fora,
        volume_solo_importado=vol_solo_importado,
        balanco_massa=balanco,
        area_corte=area_corte,
        area_aterro=area_aterro,
        elevacao_media_terreno=superficie.elevacao_media,
        remocao_vegetal=remocao_vegetal,
        categoria_solo=categoria,
    )


def calcular_cota_otima(
    superficie: SuperficieTerreno,
    espacamento: float,
    remocao_vegetal: float = 0.30,
    categoria: CategoriaSolo = CategoriaSolo.PRIMEIRA,
    tolerancia: float = 0.001,
    nome_poligono: str = "",
) -> Tuple[float, ResultadoVolume]:
    """Calcula cota otima onde corte ajustado = aterro ajustado.

    Usa biseccao (binary search). A funcao de balanco e monotonicamnete
    decrescente: cota mais alta -> mais aterro, menos corte.

    Args:
        tolerancia: Tolerancia de convergencia em m3.

    Returns:
        (cota_otima, resultado_volume)
    """
    elevacoes = superficie.elevacao_grade
    mascara_valida = ~np.isnan(elevacoes)
    elev_validas = elevacoes[mascara_valida]

    area_celula = espacamento ** 2
    fator_emp = obter_fator_empolamento(categoria)
    fator_hom = obter_fator_homogeneizacao(categoria)

    # Limites de busca
    margem = 2.0
    cota_min = float(np.nanmin(elev_validas)) - margem
    cota_max = float(np.nanmax(elev_validas)) + margem

    # Biseccao
    for _ in range(100):
        cota_meio = (cota_min + cota_max) / 2.0
        balanco = _funcao_balanco(
            cota_meio, elev_validas, area_celula,
            remocao_vegetal, fator_emp, fator_hom,
        )

        if abs(balanco) < tolerancia:
            break

        if balanco > 0:  # muito corte, subir cota
            cota_min = cota_meio
        else:  # muito aterro, baixar cota
            cota_max = cota_meio

    resultado = calcular_volumes(
        superficie, cota_meio, espacamento,
        remocao_vegetal, categoria, nome_poligono,
    )
    return cota_meio, resultado


def _funcao_balanco(
    cota: float,
    elevacoes: np.ndarray,
    area_celula: float,
    remocao_vegetal: float,
    fator_empolamento: float,
    fator_homogeneizacao: float,
) -> float:
    """Funcao auxiliar: retorna balanco de massa para uma dada cota.

    f(cota) = corte*empolamento - aterro*homogeneizacao
    Monotonicamnete decrescente em cota.
    """
    terreno_ajustado = elevacoes - remocao_vegetal
    delta = cota - terreno_ajustado

    corte = float(np.sum(np.abs(delta[delta < 0])) * area_celula)
    aterro = float(np.sum(delta[delta > 0]) * area_celula)

    return corte * fator_empolamento - aterro * fator_homogeneizacao


def calcular_volumes_por_faixas(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    espacamento: float,
    num_faixas: int = 10,
    remocao_vegetal: float = 0.30,
    categoria: CategoriaSolo = CategoriaSolo.PRIMEIRA,
) -> List[Dict]:
    """Divide o poligono em faixas e calcula volumes por segmento.

    Divide ao longo do eixo Y em faixas horizontais.

    Returns:
        Lista de dicts: {faixa, posicao_y, vol_corte, vol_aterro, balanco}
    """
    pontos = superficie.pontos_grade_xy
    elevacoes = superficie.elevacao_grade
    area_celula = espacamento ** 2

    mascara_valida = ~np.isnan(elevacoes)
    ys_validos = pontos[mascara_valida, 1]
    elev_validos = elevacoes[mascara_valida]

    y_min, y_max = float(ys_validos.min()), float(ys_validos.max())
    limites = np.linspace(y_min, y_max, num_faixas + 1)

    fator_emp = obter_fator_empolamento(categoria)
    fator_hom = obter_fator_homogeneizacao(categoria)

    faixas = []
    for i in range(num_faixas):
        mascara_faixa = (ys_validos >= limites[i]) & (ys_validos < limites[i + 1])
        if i == num_faixas - 1:
            mascara_faixa = (ys_validos >= limites[i]) & (ys_validos <= limites[i + 1])

        elev_faixa = elev_validos[mascara_faixa]
        if len(elev_faixa) == 0:
            continue

        terreno_ajustado = elev_faixa - remocao_vegetal
        delta = cota_projeto - terreno_ajustado

        vol_corte = float(np.sum(np.abs(delta[delta < 0])) * area_celula)
        vol_aterro = float(np.sum(delta[delta > 0]) * area_celula)

        posicao_y = (limites[i] + limites[i + 1]) / 2.0

        faixas.append({
            "faixa": i + 1,
            "posicao_y": posicao_y,
            "y_inicio": limites[i],
            "y_fim": limites[i + 1],
            "vol_corte": vol_corte,
            "vol_aterro": vol_aterro,
            "vol_corte_empolado": vol_corte * fator_emp,
            "vol_aterro_compactado": vol_aterro * fator_hom,
            "balanco": vol_corte * fator_emp - vol_aterro * fator_hom,
            "num_pontos": int(mascara_faixa.sum()),
        })

    return faixas
