"""Pagina: Terreno Natural 3D (Mesh3d)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_superficie_3d

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f30d Terreno Natural 3D")

nome = seletor_poligono("3d")
fig = criar_superficie_3d(
    dados["superficies"][nome],
    dados["grades"][nome],
    titulo="Terreno Natural 3D - {}".format(nome),
)
st.plotly_chart(fig, use_container_width=True)
