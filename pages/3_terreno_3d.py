"""Pagina: Terreno 3D - natural (primitivo) e plataforma desejada."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_superficie_3d, criar_plataforma_projeto_3d

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
superficie = dados["superficies"][nome]
grade = dados["grades"][nome]

# ── 1. Terreno natural (primitivo) ──
st.markdown("##### 1. Terreno natural (primitivo)")
st.caption("O relevo existente, como veio do levantamento — colorido por elevacao.")
fig_natural = criar_superficie_3d(
    superficie, grade,
    titulo="Terreno natural - {}".format(nome),
    exagero_vertical=exagero,
    cota_referencia=None,
)
st.plotly_chart(fig_natural, use_container_width=True)

# ── 2. Plataforma de projeto (terreno plano desejado) ──
st.markdown("##### 2. Plataforma de projeto (terreno plano desejado)")
st.caption(
    "O estado desejado: a superficie plana na cota de projeto ({:.2f} m). "
    "O terreno natural aparece atras, translucido, como referencia.".format(cota_ref)
)
fig_plataforma = criar_plataforma_projeto_3d(
    superficie, grade,
    cota_projeto=cota_ref,
    titulo="Plataforma de projeto - {}".format(nome),
    exagero_vertical=exagero,
)
st.plotly_chart(fig_plataforma, use_container_width=True)
