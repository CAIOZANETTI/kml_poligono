"""Coleta de elevacao via APIs externas.

Cadeia de fallback: Open-Meteo -> OpenTopoData -> Google Maps Elevation.
Baseado no padrao do repositorio kml-earthworks.
"""

import time
import math
from typing import List, Optional, Tuple

import requests

from modulos.leitor_kml import PontoKML, PoligonoKML


_TAMANHO_LOTE = 100  # pontos por requisicao
_TIMEOUT_CONEXAO = 3
_TIMEOUT_LEITURA = 10


def obter_elevacao_open_meteo(pontos: List[PontoKML]) -> List[Optional[float]]:
    """Obtem elevacao via Open-Meteo API (SRTM 30m, gratuita).

    Endpoint: https://api.open-meteo.com/v1/elevation
    """
    elevacoes: List[Optional[float]] = [None] * len(pontos)

    for inicio in range(0, len(pontos), _TAMANHO_LOTE):
        lote = pontos[inicio:inicio + _TAMANHO_LOTE]
        lats = ",".join(f"{p.latitude:.6f}" for p in lote)
        lons = ",".join(f"{p.longitude:.6f}" for p in lote)

        url = f"https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"

        try:
            resp = requests.get(url, timeout=(_TIMEOUT_CONEXAO, _TIMEOUT_LEITURA))

            if resp.status_code == 429:
                # Rate limited - extrai tempo de espera
                tempo_espera = _extrair_cooldown(resp)
                time.sleep(tempo_espera)
                resp = requests.get(url, timeout=(_TIMEOUT_CONEXAO, _TIMEOUT_LEITURA))

            if resp.status_code != 200:
                raise requests.RequestException(f"Status {resp.status_code}")

            dados = resp.json()
            valores = dados.get("elevation", [])

            for j, val in enumerate(valores):
                idx = inicio + j
                if val is not None and not math.isnan(val):
                    elevacoes[idx] = float(val)

        except (requests.RequestException, ValueError, KeyError):
            # Falha neste lote, deixa como None
            continue

        # Pequena pausa entre lotes
        if inicio + _TAMANHO_LOTE < len(pontos):
            time.sleep(0.2)

    return elevacoes


def obter_elevacao_opentopodata(pontos: List[PontoKML]) -> List[Optional[float]]:
    """Obtem elevacao via OpenTopoData API (SRTM 30m, gratuita).

    Endpoint POST: https://api.opentopodata.org/v1/srtm30m
    """
    elevacoes: List[Optional[float]] = [None] * len(pontos)

    for inicio in range(0, len(pontos), _TAMANHO_LOTE):
        lote = pontos[inicio:inicio + _TAMANHO_LOTE]
        locations = "|".join(f"{p.latitude:.6f},{p.longitude:.6f}" for p in lote)

        try:
            resp = requests.post(
                "https://api.opentopodata.org/v1/srtm30m",
                json={"locations": locations},
                timeout=(_TIMEOUT_CONEXAO, 12),
            )

            if resp.status_code != 200:
                raise requests.RequestException(f"Status {resp.status_code}")

            dados = resp.json()
            resultados = dados.get("results", [])

            for j, r in enumerate(resultados):
                idx = inicio + j
                val = r.get("elevation")
                if val is not None:
                    elevacoes[idx] = float(val)

        except (requests.RequestException, ValueError, KeyError):
            continue

        # Rate limit: 0.8s entre requests
        if inicio + _TAMANHO_LOTE < len(pontos):
            time.sleep(0.8)

    return elevacoes


def obter_elevacao_google(
    pontos: List[PontoKML],
    api_key: str,
) -> List[Optional[float]]:
    """Obtem elevacao via Google Maps Elevation API (paga, mais precisa).

    Requer chave API do Google Cloud.
    """
    elevacoes: List[Optional[float]] = [None] * len(pontos)
    tamanho_lote_google = 50  # Google tem limite menor de URL

    for inicio in range(0, len(pontos), tamanho_lote_google):
        lote = pontos[inicio:inicio + tamanho_lote_google]
        locations = "|".join(f"{p.latitude:.6f},{p.longitude:.6f}" for p in lote)

        url = (
            f"https://maps.googleapis.com/maps/api/elevation/json"
            f"?locations={locations}&key={api_key}"
        )

        try:
            resp = requests.get(url, timeout=(_TIMEOUT_CONEXAO, _TIMEOUT_LEITURA))

            if resp.status_code != 200:
                raise requests.RequestException(f"Status {resp.status_code}")

            dados = resp.json()
            if dados.get("status") != "OK":
                raise ValueError(f"Google API status: {dados.get('status')}")

            resultados = dados.get("results", [])
            for j, r in enumerate(resultados):
                idx = inicio + j
                val = r.get("elevation")
                if val is not None:
                    elevacoes[idx] = float(val)

        except (requests.RequestException, ValueError, KeyError):
            continue

        if inicio + tamanho_lote_google < len(pontos):
            time.sleep(0.1)

    return elevacoes


def obter_elevacao(
    pontos: List[PontoKML],
    api_key_google: Optional[str] = None,
    callback_progresso=None,
) -> List[Optional[float]]:
    """Obtem elevacao com cadeia de fallback.

    Ordem: Open-Meteo -> OpenTopoData -> Google Maps.

    Args:
        pontos: Lista de pontos para obter elevacao.
        api_key_google: Chave API Google (opcional).
        callback_progresso: Funcao(mensagem, progresso) para feedback.

    Returns:
        Lista de elevacoes (None onde nao foi possivel obter).
    """
    total = len(pontos)

    # 1. Open-Meteo
    if callback_progresso:
        callback_progresso("Obtendo elevacao via Open-Meteo...", 0.1)
    elevacoes = obter_elevacao_open_meteo(pontos)

    ausentes = sum(1 for e in elevacoes if e is None)
    if ausentes == 0:
        return elevacoes

    # 2. OpenTopoData para pontos ausentes
    if callback_progresso:
        callback_progresso(f"Open-Meteo: {ausentes} pontos sem dados. Tentando OpenTopoData...", 0.4)

    pontos_ausentes = [p for p, e in zip(pontos, elevacoes) if e is None]
    indices_ausentes = [i for i, e in enumerate(elevacoes) if e is None]

    if pontos_ausentes:
        elevacoes_topo = obter_elevacao_opentopodata(pontos_ausentes)
        for idx_local, idx_global in enumerate(indices_ausentes):
            if elevacoes_topo[idx_local] is not None:
                elevacoes[idx_global] = elevacoes_topo[idx_local]

    ausentes = sum(1 for e in elevacoes if e is None)
    if ausentes == 0:
        return elevacoes

    # 3. Google Maps (se chave fornecida)
    if api_key_google and ausentes > 0:
        if callback_progresso:
            callback_progresso(f"OpenTopoData: {ausentes} pontos restantes. Tentando Google...", 0.7)

        pontos_ausentes = [p for p, e in zip(pontos, elevacoes) if e is None]
        indices_ausentes = [i for i, e in enumerate(elevacoes) if e is None]

        elevacoes_google = obter_elevacao_google(pontos_ausentes, api_key_google)
        for idx_local, idx_global in enumerate(indices_ausentes):
            if elevacoes_google[idx_local] is not None:
                elevacoes[idx_global] = elevacoes_google[idx_local]

    return elevacoes


def completar_elevacao_poligono(
    poligono: PoligonoKML,
    api_key_google: Optional[str] = None,
    callback_progresso=None,
) -> PoligonoKML:
    """Preenche elevacao nos pontos de um poligono que nao tem dados 3D.

    Args:
        poligono: Poligono com pontos sem elevacao.
        api_key_google: Chave API Google opcional.
        callback_progresso: Funcao de callback para progresso.

    Returns:
        Novo PoligonoKML com elevacoes preenchidas.

    Raises:
        ValueError: Se mais de 10% dos pontos ficarem sem elevacao.
    """
    elevacoes = obter_elevacao(
        poligono.pontos,
        api_key_google=api_key_google,
        callback_progresso=callback_progresso,
    )

    novos_pontos = []
    for ponto, elev in zip(poligono.pontos, elevacoes):
        novos_pontos.append(PontoKML(
            longitude=ponto.longitude,
            latitude=ponto.latitude,
            elevacao=elev if elev is not None else ponto.elevacao,
        ))

    # Validacao: falha se >10% ausente
    total = len(novos_pontos)
    ausentes = sum(1 for p in novos_pontos if p.elevacao is None)
    if ausentes > 0:
        taxa = ausentes / total
        if taxa > 0.10:
            raise ValueError(
                f"Poligono '{poligono.nome}': {ausentes}/{total} pontos "
                f"({taxa:.0%}) sem elevacao. Limite maximo e 10%."
            )

    return PoligonoKML(
        nome=poligono.nome,
        pontos=novos_pontos,
        arquivo_origem=poligono.arquivo_origem,
        tem_elevacao=True,
    )


def _extrair_cooldown(resp: requests.Response) -> float:
    """Extrai tempo de cooldown de resposta rate-limited."""
    try:
        dados = resp.json()
        razao = dados.get("reason", "")
        # Open-Meteo retorna "... Please retry in X seconds"
        if "retry in" in razao.lower():
            partes = razao.lower().split("retry in")
            numero = "".join(c for c in partes[-1] if c.isdigit() or c == ".")
            if numero:
                return min(float(numero), 30.0)
    except Exception:
        pass
    return 2.0  # Default 2 segundos
