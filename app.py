"""Aplicacao principal Streamlit - Terraplenagem KML (multipage).

Upload e parametros ficam na pagina Home (area principal).
Os dados processados sao salvos no session_state em formato JSON
para persistir entre navegacoes de pagina.
"""

import streamlit as st

st.set_page_config(
    page_title="Terraplenagem KML",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Pages ───
pg_home = st.Page("pages/1_home.py", title="Home", default=True)
pg_contorno = st.Page("pages/2_curvas_nivel.py", title="Curvas de nivel")
pg_3d = st.Page("pages/3_terreno_3d.py", title="Terreno 3D")
pg_comp = st.Page("pages/4_comparacao_3d.py", title="Comparacao 3D")
pg_bruckner = st.Page("pages/5_bruckner.py", title="Bruckner")
pg_tabela = st.Page("pages/6_tabela_volumes.py", title="Volumes")
pg_download = st.Page("pages/7_downloads.py", title="Downloads")

nav = st.navigation({
    "principal": [pg_home],
    "visualizacoes": [pg_contorno, pg_3d, pg_comp],
    "analise": [pg_bruckner, pg_tabela],
    "exportar": [pg_download],
})

nav.run()
