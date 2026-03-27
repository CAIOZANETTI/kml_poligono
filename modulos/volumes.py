"""Calculo de volumes de corte e aterro pelo metodo de grade.

Referencia: DNIT 106/2009-ES (Cortes), DNIT 108/2009-ES (Aterros).
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

import numpy as np

from modulos.terreno import SuperficieTerreno
from modulos.geometria import GradePoligono
from modulos.taludes import calcular_volume_talude_corte, calcular_volume_talude_aterro
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
    volume_remocao_vegetal: float = 0.0   # m3 — area * espessura_remocao
    area_total_poligono: float = 0.0      # m2 — area do poligono (sem filtro NaN)
    volume_talude_corte: float = 0.0      # m3 — volume adicional talude corte
    volume_talude_aterro: float = 0.0     # m3 — volume adicional talude aterro


def calcular_volumes(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    espacamento: float,
    remocao_vegetal: float = 0.30,
    categoria: CategoriaSolo = CategoriaSolo.PRIMEIRA,
    nome_poligono: str = "",
    talude_corte_h: float = 1.0,
    talude_corte_v: float = 1.0,
    talude_aterro_h: float = 2.0,
    talude_aterro_v: float = 1.0,
    grade: Optional[GradePoligono] = None,
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
        talude_corte_h: Inclinacao horizontal do talude de corte.
        talude_corte_v: Inclinacao vertical do talude de corte.
        talude_aterro_h: Inclinacao horizontal do talude de aterro.
        talude_aterro_v: Inclinacao vertical do talude de aterro.
        grade: Grade do poligono (necessaria para calculo de taludes).

    Returns:
        ResultadoVolume com todos os volumes calculados.
    """
    area_celula = float(espacamento) ** 2
    elevacoes = superficie.elevacao_grade

    # Filtra NaN
    mascara_valida = ~np.isnan(elevacoes)
    elev_validas = elevacoes[mascara_valida]

    # Volume de remocao vegetal
    n_validas = int(np.sum(mascara_valida))
    volume_remocao_vegetal = float(n_validas * area_celula * float(remocao_vegetal))
    area_total_poligono = float(n_validas * area_celula)

    # Delta: positivo = aterro, negativo = corte
    terreno_ajustado = elev_validas - float(remocao_vegetal)
    delta = float(cota_projeto) - terreno_ajustado

    # Separar corte e aterro
    mascara_corte = delta < 0
    mascara_aterro = delta > 0

    vol_corte_bruto = float(np.sum(np.abs(delta[mascara_corte])) * area_celula)
    vol_aterro_bruto = float(np.sum(delta[mascara_aterro]) * area_celula)

    area_corte = float(int(np.sum(mascara_corte)) * area_celula)
    area_aterro = float(int(np.sum(mascara_aterro)) * area_celula)

    # Volumes de talude
    vol_talude_corte = 0.0
    vol_talude_aterro = 0.0
    if grade is not None:
        vol_talude_corte = float(calcular_volume_talude_corte(
            grade, superficie, float(cota_projeto),
            float(talude_corte_h), float(talude_corte_v), float(remocao_vegetal),
        ))
        vol_talude_aterro = float(calcular_volume_talude_aterro(
            grade, superficie, float(cota_projeto),
            float(talude_aterro_h), float(talude_aterro_v), float(remocao_vegetal),
        ))
        vol_corte_bruto += vol_talude_corte
        vol_aterro_bruto += vol_talude_aterro

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
        area_total=area_total_poligono,
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
        volume_remocao_vegetal=volume_remocao_vegetal,
        area_total_poligono=area_total_poligono,
        volume_talude_corte=vol_talude_corte,
        volume_talude_aterro=vol_talude_aterro,
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
    if len(elev_validas) == 0:
        cota_padrao = superficie.elevacao_media
        resultado = calcular_volumes(
            superficie, cota_padrao, espacamento,
            remocao_vegetal, categoria, nome_poligono,
        )
        return cota_padrao, resultado
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
    direcao: str = "norte_sul",
) -> List[Dict]:
    """Divide o poligono em faixas e calcula volumes por segmento.

    Args:
        direcao: 'norte_sul' (faixas ao longo de Y) ou 'leste_oeste' (ao longo de X).

    Returns:
        Lista de dicts com volumes por faixa.
    """
    pontos = superficie.pontos_grade_xy
    elevacoes = superficie.elevacao_grade
    area_celula = espacamento ** 2

    mascara_valida = ~np.isnan(elevacoes)
    coords_validos = pontos[mascara_valida]
    elev_validos = elevacoes[mascara_valida]

    # Eixo de corte: Y para norte-sul, X para leste-oeste
    if direcao == "leste_oeste":
        eixo_idx = 0  # corta ao longo de X
        eixo_nome = "x"
    else:
        eixo_idx = 1  # corta ao longo de Y
        eixo_nome = "y"

    eixo_validos = coords_validos[:, eixo_idx]
    eixo_min, eixo_max = float(eixo_validos.min()), float(eixo_validos.max())
    limites = np.linspace(eixo_min, eixo_max, num_faixas + 1)

    fator_emp = obter_fator_empolamento(categoria)
    fator_hom = obter_fator_homogeneizacao(categoria)

    faixas = []
    for i in range(num_faixas):
        mascara_faixa = (eixo_validos >= limites[i]) & (eixo_validos < limites[i + 1])
        if i == num_faixas - 1:
            mascara_faixa = (eixo_validos >= limites[i]) & (eixo_validos <= limites[i + 1])

        elev_faixa = elev_validos[mascara_faixa]
        if len(elev_faixa) == 0:
            continue

        terreno_ajustado = elev_faixa - remocao_vegetal
        delta = cota_projeto - terreno_ajustado

        vol_corte = float(np.sum(np.abs(delta[delta < 0])) * area_celula)
        vol_aterro = float(np.sum(delta[delta > 0]) * area_celula)

        posicao = (limites[i] + limites[i + 1]) / 2.0

        faixas.append({
            "faixa": i + 1,
            "posicao": posicao,
            "inicio": limites[i],
            "fim": limites[i + 1],
            "direcao": direcao,
            "vol_corte": vol_corte,
            "vol_aterro": vol_aterro,
            "vol_corte_empolado": vol_corte * fator_emp,
            "vol_aterro_compactado": vol_aterro * fator_hom,
            "balanco": vol_corte * fator_emp - vol_aterro * fator_hom,
            "num_pontos": int(mascara_faixa.sum()),
        })

    return faixas


def extrair_perfil_faixa(
    superficie: SuperficieTerreno,
    faixa: Dict,
    cota_projeto: float,
    espacamento: float,
    remocao_vegetal: float = 0.30,
) -> Dict:
    """Extrai perfil de terreno e projeto ao longo de uma faixa.

    Returns:
        Dict com 'posicoes', 'terreno', 'projeto', 'delta' arrays.
    """
    pontos = superficie.pontos_grade_xy
    elevacoes = superficie.elevacao_grade
    mascara_valida = ~np.isnan(elevacoes)

    direcao = faixa.get("direcao", "norte_sul")
    inicio = faixa["inicio"]
    fim = faixa["fim"]

    if direcao == "leste_oeste":
        eixo_corte = 0  # filtra por X
        eixo_perfil = 1  # perfil ao longo de Y
    else:
        eixo_corte = 1  # filtra por Y
        eixo_perfil = 0  # perfil ao longo de X

    # Pontos dentro da faixa
    mascara_faixa = (
        mascara_valida
        & (pontos[:, eixo_corte] >= inicio)
        & (pontos[:, eixo_corte] <= fim)
    )

    pos = pontos[mascara_faixa, eixo_perfil]
    elev = elevacoes[mascara_faixa]

    # Ordena por posicao
    ordem = np.argsort(pos)
    pos = pos[ordem]
    elev = elev[ordem]

    # Agrupa por posicao (media das elevacoes no mesmo ponto do eixo)
    pos_unicos = np.unique(pos)
    elev_media = np.array([
        float(np.mean(elev[pos == p])) for p in pos_unicos
    ])

    terreno_ajustado = elev_media - remocao_vegetal
    projeto = np.full_like(elev_media, cota_projeto)
    delta = cota_projeto - terreno_ajustado

    return {
        "posicoes": pos_unicos,
        "terreno": elev_media,
        "terreno_ajustado": terreno_ajustado,
        "projeto": projeto,
        "delta": delta,
    }
