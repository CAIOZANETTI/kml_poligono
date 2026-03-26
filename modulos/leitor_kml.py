"""Leitor de arquivos KML com extracao de poligonos e elevacao.

Usa xml.etree.ElementTree para parse (sem dependencia pesada de GDAL).
Suporta multiplos namespaces KML (2.2, 2.1, Google Earth).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET


# Namespaces KML comuns
_NAMESPACES = [
    "http://www.opengis.net/kml/2.2",
    "http://earth.google.com/kml/2.2",
    "http://earth.google.com/kml/2.1",
    "http://www.opengis.net/kml/2.1",
]


@dataclass
class PontoKML:
    """Ponto com coordenadas geograficas e elevacao."""
    longitude: float
    latitude: float
    elevacao: Optional[float] = None  # None se KML nao tem altitude


@dataclass
class PoligonoKML:
    """Poligono extraido de um arquivo KML."""
    nome: str
    pontos: List[PontoKML]
    arquivo_origem: str = ""
    tem_elevacao: bool = False


def _encontrar_namespace(root: ET.Element) -> str:
    """Detecta o namespace KML usado no arquivo."""
    tag = root.tag
    if "{" in tag:
        return tag[tag.find("{") + 1:tag.find("}")]
    for ns in _NAMESPACES:
        if root.find(f".//{{{ns}}}Placemark") is not None:
            return ns
    return _NAMESPACES[0]


def _parse_coordenadas(texto_coords: str) -> List[PontoKML]:
    """Converte texto de coordenadas KML para lista de PontoKML.

    Formato KML: 'lon,lat,alt lon,lat,alt ...' ou 'lon,lat lon,lat ...'
    """
    pontos = []
    partes = texto_coords.strip().split()
    for parte in partes:
        componentes = parte.strip().split(",")
        if len(componentes) < 2:
            continue
        lon = float(componentes[0])
        lat = float(componentes[1])
        elev = float(componentes[2]) if len(componentes) >= 3 else None
        pontos.append(PontoKML(longitude=lon, latitude=lat, elevacao=elev))
    return pontos


def _tem_elevacao_real(pontos: List[PontoKML]) -> bool:
    """Verifica se os pontos tem elevacao real (nao None e nao todos zero)."""
    elevacoes = [p.elevacao for p in pontos if p.elevacao is not None]
    if not elevacoes:
        return False
    # Se todos sao exatamente 0, provavelmente o KML nao tem elevacao real
    if all(e == 0.0 for e in elevacoes):
        return False
    return True


def _extrair_poligonos_placemark(
    placemark: ET.Element,
    ns: str,
    nome_arquivo: str,
    contador: List[int],
) -> List[PoligonoKML]:
    """Extrai poligonos de um Placemark (Polygon ou MultiGeometry)."""
    resultado = []
    ns_prefix = f"{{{ns}}}"

    # Nome do placemark
    nome_elem = placemark.find(f"{ns_prefix}name")
    nome_base = nome_elem.text.strip() if nome_elem is not None and nome_elem.text else ""

    # Busca Polygon direto
    poligonos_xml = placemark.findall(f".//{ns_prefix}Polygon")

    # Busca dentro de MultiGeometry
    multi = placemark.find(f".//{ns_prefix}MultiGeometry")
    if multi is not None:
        poligonos_xml.extend(multi.findall(f".//{ns_prefix}Polygon"))

    for i, poly_xml in enumerate(poligonos_xml):
        # Pega o anel externo (outerBoundaryIs)
        outer = poly_xml.find(f".//{ns_prefix}outerBoundaryIs")
        if outer is None:
            continue
        linear_ring = outer.find(f".//{ns_prefix}LinearRing")
        if linear_ring is None:
            continue
        coords_elem = linear_ring.find(f"{ns_prefix}coordinates")
        if coords_elem is None or not coords_elem.text:
            continue

        pontos = _parse_coordenadas(coords_elem.text)
        if len(pontos) < 3:
            continue

        # Remove ponto duplicado de fechamento se existir
        if (len(pontos) > 3 and
            pontos[0].longitude == pontos[-1].longitude and
            pontos[0].latitude == pontos[-1].latitude):
            pontos = pontos[:-1]

        contador[0] += 1
        nome = nome_base if nome_base else f"Poligono_{contador[0]}"
        if len(poligonos_xml) > 1:
            nome = f"{nome}_{i + 1}"

        resultado.append(PoligonoKML(
            nome=nome,
            pontos=pontos,
            arquivo_origem=nome_arquivo,
            tem_elevacao=_tem_elevacao_real(pontos),
        ))

    return resultado


def ler_arquivo_kml(conteudo_bytes: bytes, nome_arquivo: str) -> List[PoligonoKML]:
    """Le um arquivo KML e extrai todos os poligonos.

    Args:
        conteudo_bytes: Conteudo binario do arquivo KML.
        nome_arquivo: Nome do arquivo para referencia.

    Returns:
        Lista de PoligonoKML extraidos.

    Raises:
        ValueError: Se nenhum poligono valido for encontrado.
    """
    try:
        root = ET.fromstring(conteudo_bytes)
    except ET.ParseError as e:
        raise ValueError(f"Erro ao ler arquivo KML '{nome_arquivo}': {e}")

    ns = _encontrar_namespace(root)
    ns_prefix = f"{{{ns}}}"

    placemarks = root.findall(f".//{ns_prefix}Placemark")
    if not placemarks:
        raise ValueError(
            f"Nenhum Placemark encontrado em '{nome_arquivo}'. "
            "Verifique se o arquivo KML contem poligonos."
        )

    poligonos = []
    contador = [0]
    nomes_usados = set()

    for pm in placemarks:
        novos = _extrair_poligonos_placemark(pm, ns, nome_arquivo, contador)
        poligonos.extend(novos)

    # Garante nomes unicos
    for p in poligonos:
        nome_original = p.nome
        sufixo = 1
        while p.nome in nomes_usados:
            p.nome = f"{nome_original}_{sufixo}"
            sufixo += 1
        nomes_usados.add(p.nome)

    if not poligonos:
        raise ValueError(
            f"Nenhum poligono valido encontrado em '{nome_arquivo}'. "
            "O arquivo deve conter elementos <Polygon> com pelo menos 3 pontos."
        )

    return poligonos


def validar_poligono(poligono: PoligonoKML) -> Tuple[bool, str]:
    """Valida que o poligono atende requisitos minimos.

    Returns:
        (valido, mensagem_erro)
    """
    if len(poligono.pontos) < 3:
        return False, f"Poligono '{poligono.nome}' tem apenas {len(poligono.pontos)} pontos (minimo 3)."
    return True, ""


def ler_multiplos_arquivos(arquivos: list) -> List[PoligonoKML]:
    """Le multiplos arquivos KML e retorna lista consolidada de poligonos.

    Args:
        arquivos: Lista de tuplas (conteudo_bytes, nome_arquivo).

    Returns:
        Lista consolidada de PoligonoKML de todos os arquivos.
    """
    todos_poligonos = []
    nomes_globais = set()

    for conteudo, nome in arquivos:
        try:
            poligonos = ler_arquivo_kml(conteudo, nome)
            for p in poligonos:
                # Garante unicidade global
                nome_original = p.nome
                sufixo = 1
                while p.nome in nomes_globais:
                    p.nome = f"{nome_original}_{sufixo}"
                    sufixo += 1
                nomes_globais.add(p.nome)
                todos_poligonos.append(p)
        except ValueError as e:
            # Continua com outros arquivos, reporta erro
            import streamlit as st
            st.warning(str(e))

    return todos_poligonos
