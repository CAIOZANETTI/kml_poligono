"""Aplicacao principal Streamlit - Terraplenagem KML (multipage)."""

import streamlit as st

st.set_page_config(
    page_title="Terraplenagem KML",
    page_icon="\U0001f3d7\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
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
