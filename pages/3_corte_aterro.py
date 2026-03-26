"""Pagina: Mapa de Corte e Aterro."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_mapa_corte_aterro

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f534\U0001f535 Mapa de Corte e Aterro")

nome = seletor_poligono("corte_aterro")
fig = criar_mapa_corte_aterro(
    dados["superficies"][nome],
    dados["cotas"][nome],
    dados["remocao_vegetal"],
    titulo="Corte/Aterro - {}".format(nome),
)
st.plotly_chart(fig, use_container_width=True)
