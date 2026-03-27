"""Pagina: Terreno Natural 3D (Surface com Contornos)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_superficie_3d_contornos

pagina_requer_dados()
dados = obter_dados()

st.subheader("Terreno 3D")

nome = seletor_poligono("3d")

exagero = st.select_slider(
    "Exagero vertical",
    options=[1, 2, 3, 4, 5],
    value=1,
    key="exagero_3d",
)

cota_ref = dados["cotas"].get(nome)

fig = criar_superficie_3d_contornos(
    dados["superficies"][nome],
    dados["grades"][nome],
    titulo="Terreno 3D - {}".format(nome),
    exagero_vertical=exagero,
    cota_referencia=cota_ref,
)

st.plotly_chart(fig, use_container_width=True)
