"""Pagina: Comparacao 3D (Terreno vs Projeto)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_comparacao_3d

pagina_requer_dados()
dados = obter_dados()

st.title("Terreno natural vs projeto")

nome = seletor_poligono("comp")
fig = criar_comparacao_3d(
    dados["superficies"][nome],
    dados["cotas"][nome],
    dados["remocao_vegetal"],
    titulo="terreno vs projeto — {}".format(nome),
)
st.plotly_chart(fig, use_container_width=True)
