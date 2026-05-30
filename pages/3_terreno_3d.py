"""Pagina: Terreno 3D - Terreno Existente x Greide de Projeto (vista unificada)."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.visualizacao import criar_terreno_greide_3d

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
p = dados["parametros"]

st.caption(
    "**Terreno existente** (translucido, vermelho = corte / azul = aterro) e o "
    "**greide de projeto** (cinza solido = plato na cota {:.2f} m + taludes que "
    "amarram no terreno). A linha onde o terreno cruza a cota e a divisa "
    "corte/aterro.".format(cota_ref)
)

fig = criar_terreno_greide_3d(
    superficie, grade,
    cota_projeto=cota_ref,
    talude_corte_h=p.talude_corte_h,
    talude_corte_v=p.talude_corte_v,
    talude_aterro_h=p.talude_aterro_h,
    talude_aterro_v=p.talude_aterro_v,
    titulo="Terreno e greide - {}".format(nome),
    exagero_vertical=exagero,
)
st.plotly_chart(fig, use_container_width=True)
