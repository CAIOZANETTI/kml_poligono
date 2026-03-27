"""Aplicacao principal Streamlit - Terraplenagem KML (multipage).

O file_uploader e parametros ficam aqui (entry point) para persistir
entre navegacoes de pagina. Os bytes dos KML sao salvos no session_state.
"""

import streamlit as st
from modulos.parametros import (
    ParametrosPadrao, CategoriaSolo, NOMES_CATEGORIA, FATORES_DNIT,
    _resolver_categoria,
)

st.set_page_config(
    page_title="Terraplenagem KML",
    page_icon="\U0001f3d7\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Sidebar (persiste entre pages) ───
with st.sidebar:
    st.header("\U0001f4c2 Upload de Arquivos")
    arquivos_kml = st.file_uploader(
        "Arquivos KML",
        type=["kml"],
        accept_multiple_files=True,
        help="Pol\u00edgonos do Google Earth com eleva\u00e7\u00e3o",
    )

    # Salva bytes no session_state ao receber novos arquivos
    if arquivos_kml:
        novos_bytes = []
        for arq in arquivos_kml:
            conteudo = arq.read()
            arq.seek(0)
            novos_bytes.append((conteudo, arq.name))
        st.session_state["kml_bytes"] = novos_bytes
    # Se uploader foi limpo, limpa estado
    elif "kml_bytes" in st.session_state and not arquivos_kml:
        # Mantem os dados se o uploader simplesmente nao re-renderizou
        pass

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

    fatores = FATORES_DNIT[_resolver_categoria(categoria_solo)]
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

# Salva parametros no session_state
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

# ─── Pages ───
pg_home = st.Page("pages/1_home.py", title="Home", icon="\U0001f3e0", default=True)
pg_contorno = st.Page("pages/2_curvas_nivel.py", title="Curvas de N\u00edvel", icon="\U0001f5fa\ufe0f")
pg_corte = st.Page("pages/3_corte_aterro.py", title="Corte / Aterro", icon="\U0001f534")
pg_3d = st.Page("pages/4_terreno_3d.py", title="Terreno 3D", icon="\U0001f30d")
pg_comp = st.Page("pages/5_comparacao_3d.py", title="Compara\u00e7\u00e3o 3D", icon="\U0001f4ca")
pg_bruckner = st.Page("pages/6_bruckner.py", title="Diagrama de Br\u00fcckner", icon="\U0001f4c8")
pg_tabela = st.Page("pages/7_tabela_volumes.py", title="Tabela de Volumes", icon="\U0001f4cb")
pg_download = st.Page("pages/8_downloads.py", title="Downloads", icon="\U0001f4e5")

nav = st.navigation({
    "Principal": [pg_home],
    "Visualiza\u00e7\u00f5es": [pg_contorno, pg_corte, pg_3d, pg_comp],
    "An\u00e1lise": [pg_bruckner, pg_tabela],
    "Exportar": [pg_download],
})

nav.run()
