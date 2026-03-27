"""Estado compartilhado entre pages - sidebar, processamento e session_state."""

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
)


def renderizar_sidebar():
    """Renderiza sidebar com upload e parametros. Salva tudo em session_state."""
    with st.sidebar:
        st.header("\U0001f4c2 Upload de Arquivos")
        arquivos_kml = st.file_uploader(
            "Arquivos KML",
            type=["kml"],
            accept_multiple_files=True,
            help="Pol\u00edgonos do Google Earth com eleva\u00e7\u00e3o",
        )

        st.divider()
        st.header("\u2699\ufe0f Par\u00e2metros")

        espacamento = st.number_input(
            "Espa\u00e7amento da grade (m)",
            min_value=0.5, max_value=500.0, value=10.0, step=1.0,
            help="Dist\u00e2ncia entre pontos internos da grade",
        )

        remocao_vegetal = st.number_input(
            "Remo\u00e7\u00e3o vegetal (m)",
            min_value=0.0, max_value=2.0, value=0.30, step=0.05,
        )

        categoria_opcoes = {v: k for k, v in NOMES_CATEGORIA.items()}
        cat_selecionada = st.selectbox(
            "Categoria do solo",
            list(categoria_opcoes.keys()),
        )
        categoria_solo = categoria_opcoes[cat_selecionada]

        fatores = FATORES_DNIT[categoria_solo]
        st.info(
            "Empolamento: {} | Homogeneiza\u00e7\u00e3o: {}".format(
                fatores.empolamento, fatores.homogeneizacao
            )
        )

        st.divider()
        st.subheader("Taludes")
        col_tc, col_ta = st.columns(2)
        with col_tc:
            talude_corte_h = st.number_input("Corte H", value=1.0, min_value=0.1, step=0.5)
            talude_corte_v = st.number_input("Corte V", value=1.0, min_value=0.1, step=0.5)
        with col_ta:
            talude_aterro_h = st.number_input("Aterro H", value=2.0, min_value=0.1, step=0.5)
            talude_aterro_v = st.number_input("Aterro V", value=1.0, min_value=0.1, step=0.5)

        st.divider()
        st.subheader("\U0001f511 API Google (opcional)")
        api_key_google = st.text_input(
            "Chave API Google Maps",
            type="password",
            help="Fallback para eleva\u00e7\u00e3o quando Open-Meteo e OpenTopoData falham",
        )

    # Salva no session_state
    st.session_state["arquivos_kml"] = arquivos_kml
    st.session_state["espacamento"] = espacamento
    st.session_state["remocao_vegetal"] = remocao_vegetal
    st.session_state["categoria_solo"] = categoria_solo
    st.session_state["api_key_google"] = api_key_google
    st.session_state["parametros"] = ParametrosPadrao(
        espacamento_grade=espacamento,
        remocao_vegetal=remocao_vegetal,
        talude_corte_h=talude_corte_h,
        talude_corte_v=talude_corte_v,
        talude_aterro_h=talude_aterro_h,
        talude_aterro_v=talude_aterro_v,
        categoria_solo=categoria_solo,
    )


def processar_poligonos():
    """Processa KMLs e salva grades/superficies/resultados no session_state.

    Returns:
        True se dados prontos, False se nao ha arquivos.
    """
    arquivos_kml = st.session_state.get("arquivos_kml")
    if not arquivos_kml:
        return False

    espacamento = st.session_state["espacamento"]
    remocao_vegetal = st.session_state["remocao_vegetal"]
    categoria_solo = st.session_state["categoria_solo"]
    api_key = st.session_state.get("api_key_google") or None

    # Parse KML
    todos_poligonos = []
    for arq in arquivos_kml:
        try:
            conteudo = arq.read()
            arq.seek(0)  # reset para re-leitura entre pages
            polys = ler_arquivo_kml(conteudo, arq.name)
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
    """Selectbox de poligono reutilizavel. Retorna nome selecionado."""
    nomes = list(st.session_state["resultados"].keys())
    if len(nomes) == 1:
        return nomes[0]
    return st.selectbox("Pol\u00edgono", nomes, key="sel_{}".format(key))


def pagina_requer_dados():
    """Verifica se dados estao prontos. Se nao, mostra aviso e para."""
    renderizar_sidebar()
    if not processar_poligonos():
        st.info("\U0001f446 Fa\u00e7a upload de arquivos KML na barra lateral para come\u00e7ar.")
        st.stop()
