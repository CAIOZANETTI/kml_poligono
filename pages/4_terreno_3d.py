"""Pagina: Terreno Natural 3D (Surface ou Surface com Contornos)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_superficie_3d, criar_superficie_3d_contornos

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f30d Terreno Natural 3D")

nome = seletor_poligono("3d")

col_estilo, col_modo = st.columns(2)

with col_estilo:
    estilo = st.radio(
        "Estilo de visualiza\u00e7\u00e3o",
        ["Surface (Earth)", "Surface com Contornos (Viridis)"],
        horizontal=True,
        key="estilo_3d",
    )

with col_modo:
    modo_z = st.radio(
        "Eixo Z",
        ["Eleva\u00e7\u00e3o absoluta", "Altura corte(-) / aterro(+)"],
        horizontal=True,
        key="modo_z_3d",
    )

exagero = st.select_slider(
    "Exagero vertical (facilita visualiza\u00e7\u00e3o de curvas de n\u00edvel)",
    options=[1, 2, 3, 4, 5],
    value=1,
    key="exagero_3d",
)

# Determinar cota de referencia para modo relativo
cota_ref = dados["cotas"].get(nome) if modo_z == "Altura corte(-) / aterro(+)" else None

if "Contornos" in estilo:
    fig = criar_superficie_3d_contornos(
        dados["superficies"][nome],
        dados["grades"][nome],
        titulo="Terreno 3D (Contornos) - {}".format(nome),
        exagero_vertical=exagero,
        cota_referencia=cota_ref,
    )
else:
    fig = criar_superficie_3d(
        dados["superficies"][nome],
        dados["grades"][nome],
        titulo="Terreno Natural 3D - {}".format(nome),
        exagero_vertical=exagero,
        cota_referencia=cota_ref,
    )

st.plotly_chart(fig, use_container_width=True)
