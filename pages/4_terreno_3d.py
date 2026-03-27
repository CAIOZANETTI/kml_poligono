"""Pagina: Terreno Natural 3D (Surface ou Surface com Contornos)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_superficie_3d, criar_superficie_3d_contornos

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f30d Terreno Natural 3D")

nome = seletor_poligono("3d")

estilo = st.radio(
    "Estilo de visualiza\u00e7\u00e3o",
    ["Surface (Earth)", "Surface com Contornos (Viridis)"],
    horizontal=True,
    key="estilo_3d",
)

if "Contornos" in estilo:
    fig = criar_superficie_3d_contornos(
        dados["superficies"][nome],
        dados["grades"][nome],
        titulo="Terreno 3D (Contornos) - {}".format(nome),
    )
else:
    fig = criar_superficie_3d(
        dados["superficies"][nome],
        dados["grades"][nome],
        titulo="Terreno Natural 3D - {}".format(nome),
    )

st.plotly_chart(fig, use_container_width=True)
