"""Estado compartilhado entre pages - processamento e session_state.

Upload e parametros ficam na pagina Home.
Os dados processados sao serializados em JSON no session_state
para garantir persistencia durante navegacao entre paginas.
"""

import json
import streamlit as st
import numpy as np
from shapely.geometry import Polygon

from modulos.leitor_kml import ler_arquivo_kml, PoligonoKML, PontoKML
from modulos.elevacao import completar_elevacao_poligono
from modulos.geometria import processar_poligono, GradePoligono
from modulos.terreno import interpolar_terreno, SuperficieTerreno
from modulos.volumes import (
    calcular_volumes, calcular_cota_otima, ResultadoVolume,
)
from modulos.parametros import (
    ParametrosPadrao, CategoriaSolo, NOMES_CATEGORIA, FATORES_DNIT,
    _resolver_categoria,
)


# ─── Serializacao JSON ───

def _serializar_ponto(p: PontoKML) -> dict:
    return {"lon": p.longitude, "lat": p.latitude, "elev": p.elevacao}


def _desserializar_ponto(d: dict) -> PontoKML:
    return PontoKML(longitude=d["lon"], latitude=d["lat"], elevacao=d["elev"])


def _serializar_poligono_kml(poly: PoligonoKML) -> dict:
    return {
        "nome": poly.nome,
        "pontos": [_serializar_ponto(p) for p in poly.pontos],
        "arquivo_origem": poly.arquivo_origem,
        "tem_elevacao": poly.tem_elevacao,
    }


def _desserializar_poligono_kml(d: dict) -> PoligonoKML:
    return PoligonoKML(
        nome=d["nome"],
        pontos=[_desserializar_ponto(p) for p in d["pontos"]],
        arquivo_origem=d["arquivo_origem"],
        tem_elevacao=d["tem_elevacao"],
    )


def _serializar_grade(g: GradePoligono) -> dict:
    coords = list(g.poligono_shapely.exterior.coords)
    return {
        "nome": g.nome,
        "pontos_borda": g.pontos_borda.tolist(),
        "pontos_grade": g.pontos_grade.tolist(),
        "poligono_coords": coords,
        "zona_utm": g.zona_utm,
        "letra_utm": g.letra_utm,
        "espacamento": g.espacamento,
        "area": g.area,
        "perimetro": g.perimetro,
    }


def _desserializar_grade(d: dict) -> GradePoligono:
    return GradePoligono(
        nome=d["nome"],
        pontos_borda=np.array(d["pontos_borda"]),
        pontos_grade=np.array(d["pontos_grade"]),
        poligono_shapely=Polygon(d["poligono_coords"]),
        zona_utm=d["zona_utm"],
        letra_utm=d["letra_utm"],
        espacamento=d["espacamento"],
        area=d["area"],
        perimetro=d["perimetro"],
    )


def _serializar_superficie(s: SuperficieTerreno) -> dict:
    return {
        "grade_x": s.grade_x.tolist(),
        "grade_y": s.grade_y.tolist(),
        "malha_x": s.malha_x.tolist(),
        "malha_y": s.malha_y.tolist(),
        "elevacao_grade": s.elevacao_grade.tolist(),
        "elevacao_malha": _ndarray_para_lista(s.elevacao_malha),
        "elevacao_min": s.elevacao_min,
        "elevacao_max": s.elevacao_max,
        "elevacao_media": s.elevacao_media,
        "pontos_grade_xy": s.pontos_grade_xy.tolist(),
    }


def _ndarray_para_lista(arr):
    """Converte ndarray para lista, tratando NaN como None."""
    if arr.ndim == 1:
        return [None if np.isnan(v) else float(v) for v in arr]
    return [_ndarray_para_lista(row) for row in arr]


def _lista_para_ndarray(lst):
    """Converte lista de volta para ndarray, tratando None como NaN."""
    if not lst:
        return np.array([])
    if isinstance(lst[0], list):
        return np.array([[np.nan if v is None else v for v in row] for row in lst])
    return np.array([np.nan if v is None else v for v in lst])


def _desserializar_superficie(d: dict) -> SuperficieTerreno:
    return SuperficieTerreno(
        grade_x=np.array(d["grade_x"]),
        grade_y=np.array(d["grade_y"]),
        malha_x=np.array(d["malha_x"]),
        malha_y=np.array(d["malha_y"]),
        elevacao_grade=np.array(d["elevacao_grade"]),
        elevacao_malha=_lista_para_ndarray(d["elevacao_malha"]),
        elevacao_min=d["elevacao_min"],
        elevacao_max=d["elevacao_max"],
        elevacao_media=d["elevacao_media"],
        pontos_grade_xy=np.array(d["pontos_grade_xy"]),
    )


def _serializar_resultado(r: ResultadoVolume) -> dict:
    return {
        "nome_poligono": r.nome_poligono,
        "cota_projeto": r.cota_projeto,
        "area_total": r.area_total,
        "volume_corte_bruto": r.volume_corte_bruto,
        "volume_aterro_bruto": r.volume_aterro_bruto,
        "volume_corte_empolado": r.volume_corte_empolado,
        "volume_aterro_compactado": r.volume_aterro_compactado,
        "volume_bota_fora": r.volume_bota_fora,
        "volume_solo_importado": r.volume_solo_importado,
        "balanco_massa": r.balanco_massa,
        "area_corte": r.area_corte,
        "area_aterro": r.area_aterro,
        "elevacao_media_terreno": r.elevacao_media_terreno,
        "remocao_vegetal": r.remocao_vegetal,
        "categoria_solo": r.categoria_solo.value if isinstance(r.categoria_solo, CategoriaSolo) else r.categoria_solo,
    }


def _desserializar_resultado(d: dict) -> ResultadoVolume:
    return ResultadoVolume(
        nome_poligono=d["nome_poligono"],
        cota_projeto=d["cota_projeto"],
        area_total=d["area_total"],
        volume_corte_bruto=d["volume_corte_bruto"],
        volume_aterro_bruto=d["volume_aterro_bruto"],
        volume_corte_empolado=d["volume_corte_empolado"],
        volume_aterro_compactado=d["volume_aterro_compactado"],
        volume_bota_fora=d["volume_bota_fora"],
        volume_solo_importado=d["volume_solo_importado"],
        balanco_massa=d["balanco_massa"],
        area_corte=d["area_corte"],
        area_aterro=d["area_aterro"],
        elevacao_media_terreno=d["elevacao_media_terreno"],
        remocao_vegetal=d["remocao_vegetal"],
        categoria_solo=_resolver_categoria(d["categoria_solo"]),
    )


def _serializar_parametros(p: ParametrosPadrao) -> dict:
    return {
        "espacamento_grade": p.espacamento_grade,
        "remocao_vegetal": p.remocao_vegetal,
        "talude_corte_h": p.talude_corte_h,
        "talude_corte_v": p.talude_corte_v,
        "talude_aterro_h": p.talude_aterro_h,
        "talude_aterro_v": p.talude_aterro_v,
        "categoria_solo": p.categoria_solo.value if isinstance(p.categoria_solo, CategoriaSolo) else p.categoria_solo,
    }


def _desserializar_parametros(d: dict) -> ParametrosPadrao:
    return ParametrosPadrao(
        espacamento_grade=d["espacamento_grade"],
        remocao_vegetal=d["remocao_vegetal"],
        talude_corte_h=d["talude_corte_h"],
        talude_corte_v=d["talude_corte_v"],
        talude_aterro_h=d["talude_aterro_h"],
        talude_aterro_v=d["talude_aterro_v"],
        categoria_solo=_resolver_categoria(d["categoria_solo"]),
    )


# ─── Salvar / Carregar dados processados ───

def salvar_dados_sessao(poligonos, grades, superficies, resultados, cotas, parametros,
                        espacamento, remocao_vegetal, categoria_solo):
    """Serializa todos os dados processados em JSON e salva no session_state."""
    dados_json = {
        "poligonos": [_serializar_poligono_kml(p) for p in poligonos],
        "grades": {k: _serializar_grade(v) for k, v in grades.items()},
        "superficies": {k: _serializar_superficie(v) for k, v in superficies.items()},
        "resultados": {k: _serializar_resultado(v) for k, v in resultados.items()},
        "cotas": cotas,
        "parametros": _serializar_parametros(parametros),
        "espacamento": espacamento,
        "remocao_vegetal": remocao_vegetal,
        "categoria_solo": categoria_solo.value if isinstance(categoria_solo, CategoriaSolo) else categoria_solo,
    }
    st.session_state["dados_json"] = dados_json


def carregar_dados_sessao():
    """Desserializa dados JSON do session_state para objetos Python.

    Returns:
        dict com objetos reconstruidos ou None se nao ha dados.
    """
    dados_json = st.session_state.get("dados_json")
    if not dados_json:
        return None

    return {
        "poligonos": [_desserializar_poligono_kml(p) for p in dados_json["poligonos"]],
        "grades": {k: _desserializar_grade(v) for k, v in dados_json["grades"].items()},
        "superficies": {k: _desserializar_superficie(v) for k, v in dados_json["superficies"].items()},
        "resultados": {k: _desserializar_resultado(v) for k, v in dados_json["resultados"].items()},
        "cotas": dados_json["cotas"],
        "parametros": _desserializar_parametros(dados_json["parametros"]),
        "espacamento": dados_json["espacamento"],
        "remocao_vegetal": dados_json["remocao_vegetal"],
        "categoria_solo": _resolver_categoria(dados_json["categoria_solo"]),
    }


# ─── Processamento ───

def processar_poligonos():
    """Processa KMLs dos bytes no session_state.

    Returns:
        True se dados prontos, False se nao ha arquivos.
    """
    # Se ja tem dados processados no JSON, nao reprocessa
    if st.session_state.get("dados_json"):
        return True

    kml_bytes = st.session_state.get("kml_bytes")
    if not kml_bytes:
        return False

    espacamento = st.session_state.get("espacamento", 10.0)
    remocao_vegetal = st.session_state.get("remocao_vegetal", 0.30)
    categoria_solo = st.session_state.get("categoria_solo", CategoriaSolo.PRIMEIRA)

    # Parse KML a partir dos bytes salvos
    todos_poligonos = []
    for conteudo, nome_arquivo in kml_bytes:
        try:
            polys = ler_arquivo_kml(conteudo, nome_arquivo)
            todos_poligonos.extend(polys)
        except ValueError as e:
            st.error(str(e))

    if not todos_poligonos:
        return False

    # Completar elevacao (sem Google API)
    for i, poly in enumerate(todos_poligonos):
        if not poly.tem_elevacao:
            with st.spinner("Obtendo eleva\u00e7\u00e3o para '{}'...".format(poly.nome)):
                try:
                    todos_poligonos[i] = completar_elevacao_poligono(poly)
                except ValueError as e:
                    st.error(str(e))

    # Processa cada poligono
    grades = {}
    superficies = {}
    resultados = {}
    cotas = {}
    parametros = st.session_state.get("parametros", ParametrosPadrao())

    for poly in todos_poligonos:
        grade = processar_poligono(poly, espacamento)
        grades[poly.nome] = grade

        superficie = interpolar_terreno(grade)
        superficies[poly.nome] = superficie

        cota_input = superficie.elevacao_media
        cotas[poly.nome] = cota_input
        resultados[poly.nome] = calcular_volumes(
            superficie, cota_input, espacamento,
            remocao_vegetal, categoria_solo, poly.nome,
        )

    # Salva como JSON no session_state
    salvar_dados_sessao(
        todos_poligonos, grades, superficies, resultados, cotas,
        parametros, espacamento, remocao_vegetal, categoria_solo,
    )

    return True


def obter_dados():
    """Retorna dados processados do session_state ou None."""
    return carregar_dados_sessao()


def seletor_poligono(key: str) -> str:
    """Selectbox de poligono reutilizavel."""
    dados = carregar_dados_sessao()
    if not dados:
        return ""
    nomes = list(dados["resultados"].keys())
    if len(nomes) == 1:
        return nomes[0]
    return st.selectbox("Pol\u00edgono", nomes, key="sel_{}".format(key))


def pagina_requer_dados():
    """Verifica se dados estao prontos. Se nao, mostra aviso e para."""
    if not st.session_state.get("dados_json"):
        st.info("\U0001f446 Fa\u00e7a upload de arquivos KML na p\u00e1gina Home para come\u00e7ar.")
        st.stop()
