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
    "Volumes s\u00f3lidos relativos \u00e0 cota de projeto ({:.2f} m). "
    "**\U0001f7e6 Azul** = aterro necess\u00e1rio \u2014 "
    "**\U0001f7e5 Vermelho** = corte necess\u00e1rio.".format(cota_exib)
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
st.plotly_chart(fig, use_container_width=True)
