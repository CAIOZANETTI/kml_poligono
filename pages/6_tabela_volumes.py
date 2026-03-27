"""Pagina: Tabela de Volumes."""

import streamlit as st
import pandas as pd
from modulos.estado import pagina_requer_dados, obter_dados
from modulos.visualizacao import criar_tabela_volumes, criar_grafico_barras_volumes

pagina_requer_dados()
dados = obter_dados()

st.subheader("Volumes")

lista_res = list(dados["resultados"].values())

fig_tabela = criar_tabela_volumes(lista_res)
st.plotly_chart(fig_tabela, use_container_width=True)

fig_barras = criar_grafico_barras_volumes(lista_res)
st.plotly_chart(fig_barras, use_container_width=True)

st.divider()
st.subheader("Detalhamento")
df = pd.DataFrame([
    {
        "Poligono": r.nome_poligono,
        "Cota (m)": r.cota_projeto,
        "Area (m\u00b2)": r.area_total,
        "Area corte (m\u00b2)": r.area_corte,
        "Area aterro (m\u00b2)": r.area_aterro,
        "Corte bruto (m\u00b3)": r.volume_corte_bruto,
        "Aterro bruto (m\u00b3)": r.volume_aterro_bruto,
        "Corte empolado (m\u00b3)": r.volume_corte_empolado,
        "Aterro compact. (m\u00b3)": r.volume_aterro_compactado,
        "Bota-fora (m\u00b3)": r.volume_bota_fora,
        "Solo import. (m\u00b3)": r.volume_solo_importado,
        "Balanco (m\u00b3)": r.balanco_massa,
        "Rem. vegetal (m\u00b3)": r.volume_remocao_vegetal,
        "Talude corte (m\u00b3)": r.volume_talude_corte,
        "Talude aterro (m\u00b3)": r.volume_talude_aterro,
    }
    for r in lista_res
])
st.dataframe(df, use_container_width=True)
