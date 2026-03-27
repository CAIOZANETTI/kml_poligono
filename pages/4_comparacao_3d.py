"""Pagina: Comparacao 3D (Terreno vs Projeto)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_comparacao_3d

pagina_requer_dados()
dados = obter_dados()

st.subheader("Terreno natural vs projeto")

nome = seletor_poligono("comp")

cota_exib = dados["cotas"][nome]
st.info(
    "Eixo Z relativo \u00e0 cota de projeto ({:.2f} m). "
    "**Azul (acima de zero)** = aterro necess\u00e1rio. "
    "**Vermelho (abaixo de zero)** = corte necess\u00e1rio.".format(cota_exib)
)

opacidade_proj = st.slider(
    "Opacidade do plano de projeto", 0.1, 1.0, 0.5, 0.05,
    key="opac_proj_comp",
)

fig = criar_comparacao_3d(
    dados["superficies"][nome],
    cota_exib,
    dados["remocao_vegetal"],
    titulo="Terreno vs projeto - {}".format(nome),
    opacidade_projeto=opacidade_proj,
)
st.plotly_chart(fig, use_container_width=True)
