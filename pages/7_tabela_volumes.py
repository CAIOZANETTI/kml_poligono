"""Pagina: Tabela de Volumes."""

import streamlit as st
import pandas as pd
from modulos.estado import pagina_requer_dados, obter_dados
from modulos.visualizacao import criar_tabela_volumes, criar_grafico_barras_volumes

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f4cb Tabela de Volumes")

lista_res = list(dados["resultados"].values())

# Tabela Plotly
fig_tabela = criar_tabela_volumes(lista_res)
st.plotly_chart(fig_tabela, use_container_width=True)

# Barras
fig_barras = criar_grafico_barras_volumes(lista_res)
st.plotly_chart(fig_barras, use_container_width=True)

# DataFrame detalhado
st.divider()
st.subheader("Detalhamento")
df = pd.DataFrame([
    {
        "Pol\u00edgono": r.nome_poligono,
        "Cota (m)": r.cota_projeto,
        "\u00c1rea (m\u00b2)": r.area_total,
        "\u00c1rea Corte (m\u00b2)": r.area_corte,
        "\u00c1rea Aterro (m\u00b2)": r.area_aterro,
        "Corte Bruto (m\u00b3)": r.volume_corte_bruto,
        "Aterro Bruto (m\u00b3)": r.volume_aterro_bruto,
        "Corte Empolado (m\u00b3)": r.volume_corte_empolado,
        "Aterro Compact. (m\u00b3)": r.volume_aterro_compactado,
        "Bota-fora (m\u00b3)": r.volume_bota_fora,
        "Solo Import. (m\u00b3)": r.volume_solo_importado,
        "Balan\u00e7o (m\u00b3)": r.balanco_massa,
    }
    for r in lista_res
])
st.dataframe(df, use_container_width=True)
