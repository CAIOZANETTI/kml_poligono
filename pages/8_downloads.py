"""Pagina: Downloads (Memorial Gerencial, Analitico, Excel)."""

import io
import streamlit as st
import pandas as pd
from modulos.estado import pagina_requer_dados, obter_dados
from modulos.visualizacao import (
    criar_mapa_contorno, criar_mapa_corte_aterro,
    criar_superficie_3d, criar_comparacao_3d,
    criar_grafico_barras_volumes,
)
from modulos.relatorio import gerar_relatorio_html
from modulos.volumes import calcular_volumes_por_faixas
from modulos.parametros import NOMES_CATEGORIA

pagina_requer_dados()
dados = obter_dados()

st.header("\U0001f4e5 Exportar Relat\u00f3rios")

lista_res = list(dados["resultados"].values())
nomes = list(dados["resultados"].keys())
parametros = dados["parametros"]
superficies = dados["superficies"]
grades = dados["grades"]
cotas = dados["cotas"]
remocao_vegetal = dados["remocao_vegetal"]
espacamento = dados["espacamento"]
categoria = dados["categoria_solo"]

# Coleta figuras para relatorio analitico
figuras = {}
for nome in nomes:
    figuras["Curvas de N\u00edvel - {}".format(nome)] = criar_mapa_contorno(
        superficies[nome], titulo="Curvas de N\u00edvel - {}".format(nome),
    )
    figuras["Corte/Aterro - {}".format(nome)] = criar_mapa_corte_aterro(
        superficies[nome], cotas[nome], remocao_vegetal,
    )
    figuras["3D Terreno - {}".format(nome)] = criar_superficie_3d(
        superficies[nome], grades[nome],
    )
    figuras["3D Compara\u00e7\u00e3o - {}".format(nome)] = criar_comparacao_3d(
        superficies[nome], cotas[nome], remocao_vegetal,
    )

figuras["Volumes por Pol\u00edgono"] = criar_grafico_barras_volumes(lista_res)

relatorios = gerar_relatorio_html(lista_res, figuras, parametros)

st.markdown("---")

# Memorial Gerencial
st.download_button(
    label="\U0001f4cb Baixar Memorial Gerencial (.html)",
    data=relatorios["gerencial"].encode("utf-8"),
    file_name="memorial_gerencial_terraplenagem.html",
    mime="text/html",
    use_container_width=True,
    type="primary",
)

# Memorial Analitico
st.download_button(
    label="\U0001f4ca Baixar Memorial Anal\u00edtico (.html)",
    data=relatorios["analitico"].encode("utf-8"),
    file_name="memorial_analitico_terraplenagem.html",
    mime="text/html",
    use_container_width=True,
    type="primary",
)

# Planilha Excel
buffer_xlsx = io.BytesIO()
with pd.ExcelWriter(buffer_xlsx, engine="openpyxl") as writer:
    df_resumo = pd.DataFrame([
        {
            "Pol\u00edgono": r.nome_poligono,
            "Cota Projeto (m)": r.cota_projeto,
            "Eleva\u00e7\u00e3o M\u00e9dia (m)": r.elevacao_media_terreno,
            "\u00c1rea Total (m\u00b2)": r.area_total,
            "\u00c1rea Corte (m\u00b2)": r.area_corte,
            "\u00c1rea Aterro (m\u00b2)": r.area_aterro,
            "Corte Bruto (m\u00b3)": r.volume_corte_bruto,
            "Aterro Bruto (m\u00b3)": r.volume_aterro_bruto,
            "Corte Empolado (m\u00b3)": r.volume_corte_empolado,
            "Aterro Compactado (m\u00b3)": r.volume_aterro_compactado,
            "Bota-fora (m\u00b3)": r.volume_bota_fora,
            "Solo Importado (m\u00b3)": r.volume_solo_importado,
            "Balan\u00e7o (m\u00b3)": r.balanco_massa,
            "Remo\u00e7\u00e3o Vegetal (m)": r.remocao_vegetal,
            "Categoria Solo": NOMES_CATEGORIA[r.categoria_solo],
        }
        for r in lista_res
    ])
    df_resumo.to_excel(writer, sheet_name="Resumo", index=False)

    todas_faixas = []
    for nome in nomes:
        faixas = calcular_volumes_por_faixas(
            superficies[nome], cotas[nome], espacamento,
            num_faixas=10, remocao_vegetal=remocao_vegetal,
            categoria=categoria,
        )
        for f in faixas:
            f["poligono"] = nome
        todas_faixas.extend(faixas)

    if todas_faixas:
        df_faixas = pd.DataFrame(todas_faixas)
        df_faixas.to_excel(writer, sheet_name="Faixas", index=False)

st.download_button(
    label="\U0001f4c4 Baixar Planilha Excel (.xlsx)",
    data=buffer_xlsx.getvalue(),
    file_name="terraplenagem_volumes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
    type="primary",
)
