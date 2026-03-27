"""Coleta de elevacao via APIs externas.

Cadeia de fallback: Copernicus DEM GLO-30 -> Open-Meteo -> OpenTopoData -> Google Maps.
Baseado no padrao do repositorio kml-earthworks.
"""

import io
import time
import math
from typing import List, Optional, Tuple

import numpy as np
import requests

from modulos.leitor_kml import PontoKML, PoligonoKML


_TAMANHO_LOTE = 100  # pontos por requisicao
_TIMEOUT_CONEXAO = 3
_TIMEOUT_LEITURA = 10

# Cache de tiles Copernicus (chave = (lat_floor, lon_floor))
_cache_tiles_copernicus = {}

_COPERNICUS_URL = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif"
)


def _copernicus_tile_url(lat_floor: int, lon_floor: int) -> str:
    """Monta URL do tile Copernicus DEM no AWS S3."""
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return _COPERNICUS_URL.format(
        ns=ns, lat=abs(lat_floor),
        ew=ew, lon=abs(lon_floor),
    )


def _baixar_tile_copernicus(lat_floor: int, lon_floor: int) -> Optional[np.ndarray]:
    """Baixa e parseia um tile 1x1 grau do Copernicus DEM GLO-30.

    Usa tifffile para ler o GeoTIFF. Cacheia em memoria.

    Returns:
        Array 2D de elevacoes (float32) ou None se falhar.
    """
    chave = (lat_floor, lon_floor)
    if chave in _cache_tiles_copernicus:
        return _cache_tiles_copernicus[chave]

    url = _copernicus_tile_url(lat_floor, lon_floor)

    try:
        import tifffile
    except ImportError:
        return None

    try:
        resp = requests.get(url, timeout=(5, 120))
        if resp.status_code != 200:
            _cache_tiles_copernicus[chave] = None
            return None

        with tifffile.TiffFile(io.BytesIO(resp.content)) as tif:
            data = tif.pages[0].asarray()

        _cache_tiles_copernicus[chave] = data
        return data

    except Exception:
        _cache_tiles_copernicus[chave] = None
        return None


def _amostrar_elevacao_tile(
    data: np.ndarray,
    lat: float,
    lon: float,
    lat_floor: int,
    lon_floor: int,
) -> Optional[float]:
    """Amostra elevacao de um pixel no tile Copernicus.

    Cada tile cobre [lat_floor, lat_floor+1) x [lon_floor, lon_floor+1).
    Origem do raster: canto NW (topo-esquerda).
    Resolucao: 1 arcsegundo (~30m).
    """
    nrows, ncols = data.shape

    # Fracao dentro do tile (0..1)
    frac_lon = (lon - lon_floor)
    frac_lat = (lat_floor + 1 - lat)  # invertido: row 0 = norte

    col = int(frac_lon * ncols)
    row = int(frac_lat * nrows)

    # Clamp aos limites
    col = max(0, min(col, ncols - 1))
    row = max(0, min(row, nrows - 1))

    valor = float(data[row, col])

    # Nodata: Copernicus usa valores muito negativos
    if valor <= -9999.0:
        return None

    return valor


def obter_elevacao_copernicus(pontos: List[PontoKML]) -> List[Optional[float]]:
    """Obtem elevacao via Copernicus DEM GLO-30 (30m, gratuito via AWS).

    Baixa tiles 1x1 grau do bucket S3 publico copernicus-dem-30m.
    Resolucao: ~30m (1 arcsegundo). Precisao vertical: +-4m.
    Fonte: missao TanDEM-X (radar, 2010-2015).

    Returns:
        Lista de elevacoes (None onde nao foi possivel obter).
    """
    elevacoes: List[Optional[float]] = [None] * len(pontos)

    for i, p in enumerate(pontos):
        lat_floor = math.floor(p.latitude)
        lon_floor = math.floor(p.longitude)

        tile = _baixar_tile_copernicus(lat_floor, lon_floor)
        if tile is None:
            continue

        elev = _amostrar_elevacao_tile(tile, p.latitude, p.longitude, lat_floor, lon_floor)
        elevacoes[i] = elev

    return elevacoes


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

    Ordem: Copernicus DEM GLO-30 -> Open-Meteo -> OpenTopoData -> Google Maps.

    Args:
        pontos: Lista de pontos para obter elevacao.
        api_key_google: Chave API Google (opcional).
        callback_progresso: Funcao(mensagem, progresso) para feedback.

    Returns:
        Lista de elevacoes (None onde nao foi possivel obter).
    """
    total = len(pontos)

    # 1. Copernicus DEM GLO-30 (30m, gratuito, mais preciso)
    if callback_progresso:
        callback_progresso("Obtendo elevacao via Copernicus DEM GLO-30...", 0.05)
    elevacoes = obter_elevacao_copernicus(pontos)

    ausentes = sum(1 for e in elevacoes if e is None)
    if ausentes == 0:
        return elevacoes

    # 2. Open-Meteo para pontos ausentes
    if callback_progresso:
        callback_progresso(
            "Copernicus: {} pontos sem dados. Tentando Open-Meteo...".format(ausentes), 0.2,
        )

    pontos_ausentes = [p for p, e in zip(pontos, elevacoes) if e is None]
    indices_ausentes = [i for i, e in enumerate(elevacoes) if e is None]

    if pontos_ausentes:
        elevacoes_om = obter_elevacao_open_meteo(pontos_ausentes)
        for idx_local, idx_global in enumerate(indices_ausentes):
            if elevacoes_om[idx_local] is not None:
                elevacoes[idx_global] = elevacoes_om[idx_local]

    ausentes = sum(1 for e in elevacoes if e is None)
    if ausentes == 0:
        return elevacoes

    # 3. OpenTopoData para pontos ausentes
    if callback_progresso:
        callback_progresso(
            "Open-Meteo: {} pontos sem dados. Tentando OpenTopoData...".format(ausentes), 0.5,
        )

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

    # 4. Google Maps (se chave fornecida)
    if api_key_google and ausentes > 0:
        if callback_progresso:
            callback_progresso(
                "OpenTopoData: {} pontos restantes. Tentando Google...".format(ausentes), 0.7,
            )

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
