"""Pagina: Downloads (Memorial Gerencial, Analitico, Excel)."""

import io
import streamlit as st
import pandas as pd
from modulos.estado import pagina_requer_dados, obter_dados
from modulos.visualizacao import (
    criar_mapa_contorno,
    criar_superficie_3d, criar_comparacao_3d,
    criar_grafico_barras_volumes,
    criar_diagrama_bruckner as plotar_bruckner,
)
from modulos.relatorio import gerar_relatorio_html
from modulos.volumes import calcular_volumes_por_faixas
from modulos.bruckner import construir_diagrama_bruckner
from modulos.parametros import NOMES_CATEGORIA, obter_fator_empolamento, obter_fator_homogeneizacao

pagina_requer_dados()
dados = obter_dados()

st.subheader("Downloads")
st.caption("exporte relatorios e planilhas")

lista_res = list(dados["resultados"].values())
nomes = list(dados["resultados"].keys())
parametros = dados["parametros"]
superficies = dados["superficies"]
grades = dados["grades"]
cotas = dados["cotas"]
remocao_vegetal = dados["remocao_vegetal"]
espacamento = dados["espacamento"]
categoria = dados["categoria_solo"]

figuras = {}
for nome in nomes:
    figuras["Curvas de N\u00edvel - {}".format(nome)] = criar_mapa_contorno(
        superficies[nome], titulo="Curvas de N\u00edvel - {}".format(nome),
        cota_projeto=cotas[nome],
    )
    figuras["3D Terreno - {}".format(nome)] = criar_superficie_3d(
        superficies[nome], grades[nome],
    )
    figuras["3D Compara\u00e7\u00e3o - {}".format(nome)] = criar_comparacao_3d(
        superficies[nome], cotas[nome], remocao_vegetal,
    )

    # AJUSTE 4: Diagrama de Bruckner no relatorio analitico
    num_faixas_export = st.session_state.get("num_faixas_brk", 15)
    faixas_brk = calcular_volumes_por_faixas(
        superficies[nome], cotas[nome], espacamento,
        num_faixas=num_faixas_export,
        remocao_vegetal=remocao_vegetal,
        categoria=categoria,
    )
    if faixas_brk:
        resultado_brk = construir_diagrama_bruckner(
            faixas_brk,
            fator_empolamento=obter_fator_empolamento(categoria),
            fator_homogeneizacao=obter_fator_homogeneizacao(categoria),
        )
        figuras["Diagrama de Br\u00fcckner \u2014 {}".format(nome)] = plotar_bruckner(resultado_brk)

figuras["Volumes por Pol\u00edgono"] = criar_grafico_barras_volumes(lista_res)

relatorios = gerar_relatorio_html(lista_res, figuras, parametros)

st.divider()

st.download_button(
    label="Memorial gerencial (.html)",
    data=relatorios["gerencial"].encode("utf-8"),
    file_name="memorial_gerencial_terraplenagem.html",
    mime="text/html",
    use_container_width=True,
)

st.download_button(
    label="Memorial analitico (.html)",
    data=relatorios["analitico"].encode("utf-8"),
    file_name="memorial_analitico_terraplenagem.html",
    mime="text/html",
    use_container_width=True,
)

# AJUSTE 7: num_faixas from session_state
num_faixas_export = st.session_state.get("num_faixas_brk", 15)

buffer_xlsx = io.BytesIO()
with pd.ExcelWriter(buffer_xlsx, engine="openpyxl") as writer:
    df_resumo = pd.DataFrame([
        {
            "Poligono": r.nome_poligono,
            "Cota Projeto (m)": r.cota_projeto,
            "Elevacao Media (m)": r.elevacao_media_terreno,
            "Area Total (m\u00b2)": r.area_total,
            "Area Corte (m\u00b2)": r.area_corte,
            "Area Aterro (m\u00b2)": r.area_aterro,
            "Corte Bruto (m\u00b3)": r.volume_corte_bruto,
            "Aterro Bruto (m\u00b3)": r.volume_aterro_bruto,
            "Corte Empolado (m\u00b3)": r.volume_corte_empolado,
            "Aterro Compactado (m\u00b3)": r.volume_aterro_compactado,
            "Bota-fora (m\u00b3)": r.volume_bota_fora,
            "Solo Importado (m\u00b3)": r.volume_solo_importado,
            "Balanco (m\u00b3)": r.balanco_massa,
            "Remocao Vegetal (m)": r.remocao_vegetal,
            "Vol. Remocao Vegetal (m\u00b3)": r.volume_remocao_vegetal,
            "Vol. Talude Corte (m\u00b3)": r.volume_talude_corte,
            "Vol. Talude Aterro (m\u00b3)": r.volume_talude_aterro,
            "Categoria Solo": NOMES_CATEGORIA[r.categoria_solo],
        }
        for r in lista_res
    ])
    df_resumo.to_excel(writer, sheet_name="Resumo", index=False)

    todas_faixas = []
    for nome in nomes:
        faixas = calcular_volumes_por_faixas(
            superficies[nome], cotas[nome], espacamento,
            num_faixas=num_faixas_export, remocao_vegetal=remocao_vegetal,
            categoria=categoria,
        )
        for f in faixas:
            f["poligono"] = nome
        todas_faixas.extend(faixas)

    if todas_faixas:
        df_faixas = pd.DataFrame(todas_faixas)
        df_faixas.to_excel(writer, sheet_name="Faixas", index=False)

st.download_button(
    label="Planilha excel (.xlsx)",
    data=buffer_xlsx.getvalue(),
    file_name="terraplenagem_volumes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
