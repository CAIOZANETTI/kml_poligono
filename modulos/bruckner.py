"""Diagrama de Bruckner e calculo de DMT (Distancia Media de Transporte)."""

from dataclasses import dataclass, field
from typing import List, Dict

import numpy as np
import pandas as pd


@dataclass
class ResultadoBruckner:
    """Resultado do diagrama de Bruckner."""
    posicoes: np.ndarray             # posicao ao longo do eixo (m)
    volumes_acumulados: np.ndarray   # volume acumulado ajustado (m3)
    dmt: float                       # Distancia Media de Transporte (m)
    volume_bota_fora: float          # m3
    volume_solo_importado: float     # m3
    pontos_equilibrio: List[float]   # posicoes onde curva cruza zero
    faixas: List[Dict]               # dados por faixa


def construir_diagrama_bruckner(
    volumes_faixas: List[Dict],
    fator_empolamento: float = 0.77,
    fator_homogeneizacao: float = 1.00,
) -> ResultadoBruckner:
    """Constroi o diagrama de Bruckner a partir dos volumes por faixa.

    O diagrama plota volume acumulado ajustado vs posicao.
    Volume ajustado = corte * empolamento - aterro * homogeneizacao.

    Args:
        volumes_faixas: Lista de dicts com vol_corte, vol_aterro, posicao_y.
        fator_empolamento: Fator de empolamento DNIT.
        fator_homogeneizacao: Fator de homogeneizacao DNIT.

    Returns:
        ResultadoBruckner com curva de massa e DMT.
    """
    if not volumes_faixas:
        return ResultadoBruckner(
            posicoes=np.array([]),
            volumes_acumulados=np.array([]),
            dmt=0.0,
            volume_bota_fora=0.0,
            volume_solo_importado=0.0,
            pontos_equilibrio=[],
            faixas=[],
        )

    n = len(volumes_faixas)
    posicoes = np.zeros(n + 1)
    volumes_acum = np.zeros(n + 1)

    for i, faixa in enumerate(volumes_faixas):
        posicoes[i + 1] = faixa["posicao_y"]
        balanco_faixa = (
            faixa["vol_corte"] * fator_empolamento
            - faixa["vol_aterro"] * fator_homogeneizacao
        )
        volumes_acum[i + 1] = volumes_acum[i] + balanco_faixa

    # Posicao inicial = primeira faixa
    posicoes[0] = volumes_faixas[0].get("y_inicio", posicoes[1] - 1.0)

    # Encontra pontos de equilibrio (zero-crossings)
    pontos_eq = _encontrar_cruzamentos_zero(posicoes, volumes_acum)

    # Calcula DMT
    dmt = calcular_dmt(volumes_faixas, fator_empolamento, fator_homogeneizacao)

    # Bota-fora e solo importado
    vol_final = volumes_acum[-1]
    vol_bota_fora = max(0.0, vol_final)
    vol_solo_importado = max(0.0, -vol_final)

    return ResultadoBruckner(
        posicoes=posicoes,
        volumes_acumulados=volumes_acum,
        dmt=dmt,
        volume_bota_fora=vol_bota_fora,
        volume_solo_importado=vol_solo_importado,
        pontos_equilibrio=pontos_eq,
        faixas=volumes_faixas,
    )


def calcular_dmt(
    volumes_faixas: List[Dict],
    fator_empolamento: float = 0.77,
    fator_homogeneizacao: float = 1.00,
) -> float:
    """Calcula a Distancia Media de Transporte.

    DMT = sum(|Vi| * Di) / sum(|Vi|)

    Onde Vi e o balanco de cada faixa e Di e a distancia ao centroide.
    """
    if not volumes_faixas:
        return 0.0

    # Centroide de massa
    posicoes = np.array([f["posicao_y"] for f in volumes_faixas])
    balancos = np.array([
        f["vol_corte"] * fator_empolamento - f["vol_aterro"] * fator_homogeneizacao
        for f in volumes_faixas
    ])

    volumes_abs = np.abs(balancos)
    soma_vol = np.sum(volumes_abs)

    if soma_vol < 1e-6:
        return 0.0

    centroide = np.sum(posicoes * volumes_abs) / soma_vol

    # DMT = media ponderada das distancias ao centroide
    distancias = np.abs(posicoes - centroide)
    dmt = float(np.sum(volumes_abs * distancias) / soma_vol)

    return dmt


def identificar_zonas_transporte(
    resultado: ResultadoBruckner,
) -> pd.DataFrame:
    """Identifica zonas de transporte do diagrama de Bruckner.

    Returns:
        DataFrame com colunas: zona, inicio, fim, volume, distancia, tipo.
    """
    if len(resultado.faixas) == 0:
        return pd.DataFrame(columns=["zona", "inicio", "fim", "volume", "distancia", "tipo"])

    zonas = []
    eq_pts = sorted(resultado.pontos_equilibrio)

    # Adiciona limites
    pos_min = resultado.posicoes[0]
    pos_max = resultado.posicoes[-1]
    limites = [pos_min] + eq_pts + [pos_max]

    for i in range(len(limites) - 1):
        inicio = limites[i]
        fim = limites[i + 1]
        meio = (inicio + fim) / 2.0

        # Volume nesta zona
        mascara = [
            f for f in resultado.faixas
            if f["posicao_y"] >= inicio and f["posicao_y"] <= fim
        ]
        vol_total = sum(f.get("balanco", 0) for f in mascara)

        if abs(vol_total) < 0.01:
            tipo = "equilibrado"
        elif vol_total > 0:
            tipo = "bota_fora"
        else:
            tipo = "emprestimo"

        zonas.append({
            "zona": i + 1,
            "inicio": inicio,
            "fim": fim,
            "volume": abs(vol_total),
            "distancia": fim - inicio,
            "tipo": tipo,
        })

    return pd.DataFrame(zonas)


def _encontrar_cruzamentos_zero(
    posicoes: np.ndarray,
    volumes: np.ndarray,
) -> List[float]:
    """Encontra posicoes onde a curva acumulada cruza zero."""
    cruzamentos = []
    for i in range(len(volumes) - 1):
        if volumes[i] * volumes[i + 1] < 0:
            # Interpolacao linear para encontrar o cruzamento
            frac = abs(volumes[i]) / (abs(volumes[i]) + abs(volumes[i + 1]))
            pos = posicoes[i] + frac * (posicoes[i + 1] - posicoes[i])
            cruzamentos.append(float(pos))
    return cruzamentos
