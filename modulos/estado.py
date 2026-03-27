"""Estado compartilhado entre pages - processamento e session_state.

O upload e parametros ficam no app.py (entry point).
Este modulo le os bytes ja salvos no session_state.
"""

import streamlit as st

from modulos.leitor_kml import ler_arquivo_kml, PoligonoKML
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


def processar_poligonos():
    """Processa KMLs dos bytes no session_state.

    Returns:
        True se dados prontos, False se nao ha arquivos.
    """
    kml_bytes = st.session_state.get("kml_bytes")
    if not kml_bytes:
        return False

    espacamento = st.session_state.get("espacamento", 10.0)
    remocao_vegetal = st.session_state.get("remocao_vegetal", 0.30)
    categoria_solo = st.session_state.get("categoria_solo", CategoriaSolo.PRIMEIRA)
    api_key = st.session_state.get("api_key_google") or None

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

    # Completar elevacao
    for i, poly in enumerate(todos_poligonos):
        if not poly.tem_elevacao:
            with st.spinner("Obtendo eleva\u00e7\u00e3o para '{}'...".format(poly.nome)):
                try:
                    todos_poligonos[i] = completar_elevacao_poligono(poly, api_key_google=api_key)
                except ValueError as e:
                    st.error(str(e))

    # Processa cada poligono
    grades = {}
    superficies = {}
    resultados = {}
    cotas = {}

    for poly in todos_poligonos:
        grade = processar_poligono(poly, espacamento)
        grades[poly.nome] = grade

        superficie = interpolar_terreno(grade)
        superficies[poly.nome] = superficie

        # Cota: verifica se usuario selecionou cota otima
        usar_otima = st.session_state.get("otima_{}".format(poly.nome), False)
        cota_input = st.session_state.get("cota_{}".format(poly.nome), superficie.elevacao_media)

        if usar_otima:
            cota_ot, res_ot = calcular_cota_otima(
                superficie, espacamento, remocao_vegetal,
                categoria_solo, nome_poligono=poly.nome,
            )
            cotas[poly.nome] = cota_ot
            resultados[poly.nome] = res_ot
        else:
            cotas[poly.nome] = cota_input
            resultados[poly.nome] = calcular_volumes(
                superficie, cota_input, espacamento,
                remocao_vegetal, categoria_solo, poly.nome,
            )

    # Salva no session_state
    st.session_state["todos_poligonos"] = todos_poligonos
    st.session_state["grades"] = grades
    st.session_state["superficies"] = superficies
    st.session_state["resultados"] = resultados
    st.session_state["cotas"] = cotas

    return True


def obter_dados():
    """Retorna dados processados do session_state ou None."""
    if "resultados" not in st.session_state:
        return None
    return {
        "poligonos": st.session_state["todos_poligonos"],
        "grades": st.session_state["grades"],
        "superficies": st.session_state["superficies"],
        "resultados": st.session_state["resultados"],
        "cotas": st.session_state["cotas"],
        "parametros": st.session_state["parametros"],
        "espacamento": st.session_state["espacamento"],
        "remocao_vegetal": st.session_state["remocao_vegetal"],
        "categoria_solo": st.session_state["categoria_solo"],
    }


def seletor_poligono(key: str) -> str:
    """Selectbox de poligono reutilizavel."""
    nomes = list(st.session_state["resultados"].keys())
    if len(nomes) == 1:
        return nomes[0]
    return st.selectbox("Pol\u00edgono", nomes, key="sel_{}".format(key))


def pagina_requer_dados():
    """Verifica se dados estao prontos. Se nao, mostra aviso e para."""
    if not processar_poligonos():
        st.info("\U0001f446 Fa\u00e7a upload de arquivos KML na p\u00e1gina Home para come\u00e7ar.")
        st.stop()
