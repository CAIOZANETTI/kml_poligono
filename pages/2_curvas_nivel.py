"""Pagina: Curvas de Nivel."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_mapa_contorno

pagina_requer_dados()
dados = obter_dados()

st.title("Curvas de nivel")

nome = seletor_poligono("contorno")
fig = criar_mapa_contorno(
    dados["superficies"][nome],
    titulo="curvas de nivel — {}".format(nome),
)
st.plotly_chart(fig, use_container_width=True)
