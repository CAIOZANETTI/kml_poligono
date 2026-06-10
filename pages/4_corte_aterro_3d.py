"""Pagina: Corte e Aterro 3D."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_corte_aterro_3d

pagina_requer_dados()
dados = obter_dados()

st.subheader("Corte e Aterro 3D")

nome = seletor_poligono("comp")

cota_exib = dados["cotas"][nome]
st.info(
    "Eleva\u00e7\u00e3o real com a plataforma de projeto ({:.2f} m) como plano cinza. "
    "**\U0001f7e5 Vermelho (corte)** = terreno acima do plano \u2014 "
    "**\U0001f7e6 Azul (aterro)** = vazio preenchido at\u00e9 o plano.".format(cota_exib)
)

opacidade_proj = st.slider(
    "Opacidade da plataforma de projeto", 0.1, 1.0, 0.5, 0.05,
    key="opac_proj_comp",
)

fig = criar_corte_aterro_3d(
    dados["superficies"][nome],
    cota_exib,
    dados["remocao_vegetal"],
    titulo="Corte e Aterro - {}".format(nome),
    opacidade_projeto=opacidade_proj,
)
st.plotly_chart(fig, width="stretch")
