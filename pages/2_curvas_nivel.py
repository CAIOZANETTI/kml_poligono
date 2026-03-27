"""Pagina: Curvas de Nivel."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_mapa_contorno

pagina_requer_dados()
dados = obter_dados()

st.subheader("Curvas de nivel")

nome = seletor_poligono("contorno")

equidistancia = st.selectbox(
    "Equidistancia (m)",
    [0.25, 0.5, 1.0, 2.0, 5.0],
    index=2,
    key="equidist_contorno",
)

fig = criar_mapa_contorno(
    dados["superficies"][nome],
    titulo="Curvas de nivel - {}".format(nome),
    cota_projeto=dados["cotas"][nome],
    equidistancia=equidistancia,
)
st.plotly_chart(fig, use_container_width=True)
