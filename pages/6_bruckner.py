"""Pagina: Diagrama de Bruckner e DMT."""

import streamlit as st
import pandas as pd
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.volumes import calcular_volumes_por_faixas
from modulos.bruckner import construir_diagrama_bruckner, identificar_zonas_transporte
from modulos.visualizacao import criar_diagrama_bruckner as plotar_bruckner
from modulos.parametros import obter_fator_empolamento, obter_fator_homogeneizacao

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f4c8 Diagrama de Br\u00fcckner")

nome = seletor_poligono("bruckner")

espacamento = dados["espacamento"]
remocao_vegetal = dados["remocao_vegetal"]
categoria = dados["categoria_solo"]
cota = dados["cotas"][nome]

# Calcula faixas e diagrama
faixas = calcular_volumes_por_faixas(
    dados["superficies"][nome], cota, espacamento,
    num_faixas=15, remocao_vegetal=remocao_vegetal,
    categoria=categoria,
)

resultado_brk = construir_diagrama_bruckner(
    faixas,
    fator_empolamento=obter_fator_empolamento(categoria),
    fator_homogeneizacao=obter_fator_homogeneizacao(categoria),
)

# Grafico
fig = plotar_bruckner(resultado_brk)
st.plotly_chart(fig, use_container_width=True)

# Metricas
st.divider()
b1, b2, b3 = st.columns(3)
b1.metric("DMT", "{:,.1f} m".format(resultado_brk.dmt))
b2.metric("Bota-fora", "{:,.1f} m\u00b3".format(resultado_brk.volume_bota_fora))
b3.metric("Solo Importado", "{:,.1f} m\u00b3".format(resultado_brk.volume_solo_importado))

# Zonas de transporte
st.divider()
st.subheader("Zonas de Transporte")
df_zonas = identificar_zonas_transporte(resultado_brk)
if not df_zonas.empty:
    st.dataframe(df_zonas, use_container_width=True)
else:
    st.info("Nenhuma zona de transporte identificada.")

# Tabela de faixas
st.divider()
st.subheader("Volumes por Faixa")
if faixas:
    df_faixas = pd.DataFrame(faixas)
    colunas_exibir = [
        "faixa", "posicao_y", "vol_corte", "vol_aterro",
        "vol_corte_empolado", "vol_aterro_compactado", "balanco",
    ]
    colunas_disponiveis = [c for c in colunas_exibir if c in df_faixas.columns]
    st.dataframe(df_faixas[colunas_disponiveis], use_container_width=True)
