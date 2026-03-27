"""Pagina: Diagrama de Bruckner."""

import streamlit as st
import pandas as pd
import numpy as np
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.volumes import calcular_volumes_por_faixas, extrair_perfil_faixa
from modulos.bruckner import construir_diagrama_bruckner, identificar_zonas_transporte
from modulos.visualizacao import criar_diagrama_bruckner as plotar_bruckner, criar_perfil_faixa
from modulos.parametros import obter_fator_empolamento, obter_fator_homogeneizacao

pagina_requer_dados()
dados = obter_dados()

st.subheader("Diagrama de Bruckner")

nome = seletor_poligono("bruckner")

espacamento = dados["espacamento"]
remocao_vegetal = dados["remocao_vegetal"]
categoria = dados["categoria_solo"]
cota = dados["cotas"][nome]
superficie = dados["superficies"][nome]

col_dir, col_faixas = st.columns([2, 1])
with col_dir:
    direcao = st.radio(
        "Direcao do corte",
        ["Norte-Sul (ao longo de Y)", "Leste-Oeste (ao longo de X)"],
        horizontal=True,
        key="dir_bruckner",
    )
    direcao_key = "norte_sul" if "Norte" in direcao else "leste_oeste"

with col_faixas:
    num_faixas = st.slider(
        "Numero de faixas",
        min_value=3, max_value=50, value=15, step=1,
        key="num_faixas_brk",
    )

faixas = calcular_volumes_por_faixas(
    superficie, cota, espacamento,
    num_faixas=int(num_faixas),
    remocao_vegetal=remocao_vegetal,
    categoria=categoria,
    direcao=direcao_key,
)

if not faixas:
    st.warning("Nenhuma faixa calculada.")
    st.stop()

resultado_brk = construir_diagrama_bruckner(
    faixas,
    fator_empolamento=obter_fator_empolamento(categoria),
    fator_homogeneizacao=obter_fator_homogeneizacao(categoria),
)

fig_brk = plotar_bruckner(resultado_brk)
st.plotly_chart(fig_brk, use_container_width=True)

b1, b2, b3 = st.columns(3)
b1.metric(
    "DMT",
    "{:,.1f} m".format(resultado_brk.dmt),
    delta="{} faixas".format(len(faixas)),
    delta_color="off",
)
b2.metric(
    "Bota-fora",
    "{:,.1f} m\u00b3".format(resultado_brk.volume_bota_fora),
    delta="excesso" if resultado_brk.volume_bota_fora > 0 else "zero",
    delta_color="inverse" if resultado_brk.volume_bota_fora > 0 else "off",
)
b3.metric(
    "Solo importado",
    "{:,.1f} m\u00b3".format(resultado_brk.volume_solo_importado),
    delta="deficit" if resultado_brk.volume_solo_importado > 0 else "zero",
    delta_color="inverse" if resultado_brk.volume_solo_importado > 0 else "off",
)

# ─── Volumes por faixa ───
st.divider()
st.subheader("Volumes por faixa")

df_faixas = pd.DataFrame(faixas)
colunas_exibir = [
    "faixa", "posicao", "vol_corte", "vol_aterro",
    "vol_corte_empolado", "vol_aterro_compactado", "balanco",
]
colunas_disponiveis = [c for c in colunas_exibir if c in df_faixas.columns]
st.dataframe(df_faixas[colunas_disponiveis], use_container_width=True)

# ─── Perfil da faixa ───
st.divider()
st.subheader("Perfil da faixa")

opcoes_faixa = ["Faixa {} (pos: {:.1f}m)".format(f["faixa"], f["posicao"]) for f in faixas]
idx_selecionado = st.selectbox(
    "Selecione a faixa",
    range(len(opcoes_faixa)),
    format_func=lambda i: opcoes_faixa[i],
    key="sel_faixa_brk",
)

faixa_sel = faixas[idx_selecionado]

fc1, fc2, fc3 = st.columns(3)
fc1.metric(
    "Corte empolado",
    "{:,.2f} m\u00b3".format(faixa_sel["vol_corte_empolado"]),
    delta="{:,.2f} m\u00b3 bruto".format(faixa_sel["vol_corte"]),
    delta_color="off",
)
fc2.metric(
    "Aterro compactado",
    "{:,.2f} m\u00b3".format(faixa_sel["vol_aterro_compactado"]),
    delta="{:,.2f} m\u00b3 bruto".format(faixa_sel["vol_aterro"]),
    delta_color="off",
)
bal = faixa_sel["balanco"]
fc3.metric(
    "Balanco",
    "{:,.2f} m\u00b3".format(bal),
    delta="corte > aterro" if bal > 0 else "aterro > corte" if bal < 0 else "equilibrado",
    delta_color="normal" if bal >= 0 else "inverse",
)

perfil = extrair_perfil_faixa(
    superficie, faixa_sel, cota, espacamento, remocao_vegetal,
)

if len(perfil["posicoes"]) > 1:
    dir_label = "N-S" if direcao_key == "norte_sul" else "L-O"
    fig_perfil = criar_perfil_faixa(
        perfil, faixa_sel,
        titulo="Perfil faixa {} ({}) - {}".format(faixa_sel["faixa"], dir_label, nome),
    )
    st.plotly_chart(fig_perfil, use_container_width=True)
else:
    st.info("Faixa com poucos pontos para gerar perfil.")

# ─── Zonas de transporte ───
st.divider()
st.subheader("Zonas de transporte")
df_zonas = identificar_zonas_transporte(resultado_brk)
if not df_zonas.empty:
    st.dataframe(df_zonas, use_container_width=True)
else:
    st.info("Nenhuma zona de transporte identificada.")
