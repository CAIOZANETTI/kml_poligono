"""Aplicacao principal Streamlit para calculo de terraplenagem."""

import io
import streamlit as st
import pandas as pd
import numpy as np

from modulos.leitor_kml import ler_arquivo_kml, PoligonoKML
from modulos.elevacao import completar_elevacao_poligono
from modulos.geometria import processar_poligono, GradePoligono
from modulos.terreno import interpolar_terreno, SuperficieTerreno
from modulos.volumes import (
    calcular_volumes, calcular_cota_otima,
    calcular_volumes_por_faixas, ResultadoVolume,
)
from modulos.taludes import (
    calcular_volume_talude_corte, calcular_volume_talude_aterro,
)
from modulos.bruckner import construir_diagrama_bruckner, ResultadoBruckner
from modulos.visualizacao import (
    criar_mapa_contorno, criar_superficie_3d, criar_comparacao_3d,
    criar_mapa_corte_aterro, criar_perfil_transversal,
    criar_diagrama_bruckner as plotar_bruckner,
    criar_tabela_volumes, criar_grafico_barras_volumes,
)
from modulos.relatorio import gerar_relatorio_html
from modulos.parametros import (
    ParametrosPadrao, CategoriaSolo, NOMES_CATEGORIA,
    FATORES_DNIT, obter_fator_empolamento, obter_fator_homogeneizacao,
)

# ─── Configuracao da pagina ───
st.set_page_config(
    page_title="Terraplenagem KML",
    page_icon="\U0001f3d7\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("\U0001f3d7\ufe0f Terraplenagem - C\u00e1lculo de Volumes")
st.caption("Importe pol\u00edgonos KML do Google Earth para calcular corte e aterro")


# ─── Sidebar: Parametros ───
with st.sidebar:
    st.header("\U0001f4c2 Upload de Arquivos")
    arquivos_kml = st.file_uploader(
        "Arquivos KML",
        type=["kml"],
        accept_multiple_files=True,
        help="Pol\u00edgonos do Google Earth com eleva\u00e7\u00e3o",
    )

    st.divider()
    st.header("\u2699\ufe0f Par\u00e2metros")

    espacamento = st.number_input(
        "Espa\u00e7amento da grade (m)",
        min_value=0.5, max_value=10.0, value=1.0, step=0.5,
        help="Dist\u00e2ncia entre pontos internos da grade",
    )

    remocao_vegetal = st.number_input(
        "Remo\u00e7\u00e3o vegetal (m)",
        min_value=0.0, max_value=2.0, value=0.30, step=0.05,
    )

    categoria_opcoes = {v: k for k, v in NOMES_CATEGORIA.items()}
    cat_selecionada = st.selectbox(
        "Categoria do solo",
        list(categoria_opcoes.keys()),
    )
    categoria_solo = categoria_opcoes[cat_selecionada]

    fatores = FATORES_DNIT[categoria_solo]
    st.info(f"Empolamento: {fatores.empolamento} | Homogeneiza\u00e7\u00e3o: {fatores.homogeneizacao}")

    st.divider()
    st.subheader("Taludes")
    col_tc, col_ta = st.columns(2)
    with col_tc:
        talude_corte_h = st.number_input("Corte H", value=1.0, min_value=0.1, step=0.5)
        talude_corte_v = st.number_input("Corte V", value=1.0, min_value=0.1, step=0.5)
    with col_ta:
        talude_aterro_h = st.number_input("Aterro H", value=2.0, min_value=0.1, step=0.5)
        talude_aterro_v = st.number_input("Aterro V", value=1.0, min_value=0.1, step=0.5)

    st.divider()
    st.subheader("\U0001f511 API Google (opcional)")
    api_key_google = st.text_input(
        "Chave API Google Maps",
        type="password",
        help="Usado como fallback para eleva\u00e7\u00e3o quando Open-Meteo e OpenTopoData falham",
    )


# ─── Parametros consolidados ───
parametros = ParametrosPadrao(
    espacamento_grade=espacamento,
    remocao_vegetal=remocao_vegetal,
    talude_corte_h=talude_corte_h,
    talude_corte_v=talude_corte_v,
    talude_aterro_h=talude_aterro_h,
    talude_aterro_v=talude_aterro_v,
    categoria_solo=categoria_solo,
)


# ─── Processamento ───
if not arquivos_kml:
    st.info("\U0001f446 Fa\u00e7a upload de arquivos KML na barra lateral para come\u00e7ar.")
    st.stop()

# Parse KML
todos_poligonos: list[PoligonoKML] = []
for arq in arquivos_kml:
    try:
        conteudo = arq.read()
        polys = ler_arquivo_kml(conteudo, arq.name)
        todos_poligonos.extend(polys)
    except ValueError as e:
        st.error(str(e))

if not todos_poligonos:
    st.error("Nenhum pol\u00edgono v\u00e1lido encontrado nos arquivos KML.")
    st.stop()

# Completar elevacao se necessario
for i, poly in enumerate(todos_poligonos):
    if not poly.tem_elevacao:
        with st.spinner(f"Obtendo eleva\u00e7\u00e3o para '{poly.nome}'..."):
            try:
                todos_poligonos[i] = completar_elevacao_poligono(
                    poly,
                    api_key_google=api_key_google if api_key_google else None,
                )
                st.success(f"\u2705 Eleva\u00e7\u00e3o obtida para '{poly.nome}'")
            except ValueError as e:
                st.error(str(e))

# ─── Secao: Poligonos Carregados ───
st.header(f"\U0001f4cd Pol\u00edgonos Carregados ({len(todos_poligonos)})")

# Dicionarios de estado
grades: dict[str, GradePoligono] = {}
superficies: dict[str, SuperficieTerreno] = {}
resultados: dict[str, ResultadoVolume] = {}
cotas: dict[str, float] = {}
usar_otima: dict[str, bool] = {}

for poly in todos_poligonos:
    grade = processar_poligono(poly, espacamento)
    grades[poly.nome] = grade

    superficie = interpolar_terreno(grade)
    superficies[poly.nome] = superficie

    with st.expander(f"\U0001f4d0 {poly.nome}", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pontos", len(poly.pontos))
        c2.metric("\u00c1rea", f"{grade.area:,.0f} m\u00b2")
        c3.metric("Per\u00edmetro", f"{grade.perimetro:,.0f} m")
        c4.metric("Elev. M\u00edn", f"{superficie.elevacao_min:.2f} m")
        c5.metric("Elev. M\u00e1x", f"{superficie.elevacao_max:.2f} m")

        col_cota, col_otima = st.columns([3, 1])
        with col_cota:
            cota_input = st.number_input(
                "Cota do projeto (m)",
                value=round(superficie.elevacao_media, 2),
                step=0.10,
                format="%.2f",
                key=f"cota_{poly.nome}",
            )
        with col_otima:
            st.write("")  # spacer
            usar_cota_otima = st.checkbox(
                "Cota \u00f3tima",
                key=f"otima_{poly.nome}",
                help="Calcula automaticamente a cota onde corte = aterro",
            )

        if usar_cota_otima:
            cota_ot, res_ot = calcular_cota_otima(
                superficie, espacamento, remocao_vegetal,
                categoria_solo, nome_poligono=poly.nome,
            )
            st.success(f"Cota \u00f3tima calculada: **{cota_ot:.2f} m** (balan\u00e7o: {res_ot.balanco_massa:.2f} m\u00b3)")
            cotas[poly.nome] = cota_ot
            usar_otima[poly.nome] = True
            resultados[poly.nome] = res_ot
        else:
            cotas[poly.nome] = cota_input
            usar_otima[poly.nome] = False
            resultados[poly.nome] = calcular_volumes(
                superficie, cota_input, espacamento,
                remocao_vegetal, categoria_solo, poly.nome,
            )

# ─── Metricas resumo ───
st.divider()
lista_resultados = list(resultados.values())

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Total Corte Empolado", f"{sum(r.volume_corte_empolado for r in lista_resultados):,.1f} m\u00b3")
mc2.metric("Total Aterro Compactado", f"{sum(r.volume_aterro_compactado for r in lista_resultados):,.1f} m\u00b3")
mc3.metric("Bota-fora", f"{sum(r.volume_bota_fora for r in lista_resultados):,.1f} m\u00b3")
mc4.metric("Solo Importado", f"{sum(r.volume_solo_importado for r in lista_resultados):,.1f} m\u00b3")


# ─── Tabs de visualizacao ───
st.divider()
nomes_poly = list(resultados.keys())

tab_contorno, tab_corte_aterro, tab_3d, tab_comp, tab_perfil, tab_bruckner, tab_tabela, tab_download = st.tabs([
    "\U0001f5fa\ufe0f Curvas de N\u00edvel",
    "\U0001f534\U0001f535 Corte/Aterro",
    "\U0001f30d 3D Terreno",
    "\U0001f4ca 3D Compara\u00e7\u00e3o",
    "\U0001f4cf Perfil Transversal",
    "\U0001f4c8 Br\u00fcckner",
    "\U0001f4cb Tabela de Volumes",
    "\U0001f4e5 Downloads",
])

# Seletor de poligono (reutilizado)
def _seletor(tab_key: str) -> str:
    if len(nomes_poly) == 1:
        return nomes_poly[0]
    return st.selectbox("Pol\u00edgono", nomes_poly, key=f"sel_{tab_key}")


with tab_contorno:
    nome = _seletor("contorno")
    fig = criar_mapa_contorno(superficies[nome], titulo=f"Curvas de N\u00edvel - {nome}")
    st.plotly_chart(fig, use_container_width=True)

with tab_corte_aterro:
    nome = _seletor("corte_aterro")
    fig = criar_mapa_corte_aterro(
        superficies[nome], cotas[nome], remocao_vegetal,
        titulo=f"Corte/Aterro - {nome}",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_3d:
    nome = _seletor("3d")
    fig = criar_superficie_3d(
        superficies[nome], grades[nome],
        titulo=f"Terreno Natural 3D - {nome}",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_comp:
    nome = _seletor("comp")
    fig = criar_comparacao_3d(
        superficies[nome], cotas[nome], remocao_vegetal,
        titulo=f"Terreno vs Projeto - {nome}",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_perfil:
    nome = _seletor("perfil")
    sup = superficies[nome]
    y_min = float(sup.grade_y.min())
    y_max = float(sup.grade_y.max())
    y_meio = (y_min + y_max) / 2.0

    pos_y = st.slider(
        "Posi\u00e7\u00e3o Y do corte (m)",
        min_value=y_min, max_value=y_max, value=y_meio,
        step=float(espacamento),
        key="slider_perfil",
    )
    fig = criar_perfil_transversal(
        sup, grades[nome], cotas[nome], pos_y,
        remocao_vegetal,
        talude_corte=(talude_corte_h, talude_corte_v),
        talude_aterro=(talude_aterro_h, talude_aterro_v),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_bruckner:
    nome = _seletor("bruckner")
    faixas = calcular_volumes_por_faixas(
        superficies[nome], cotas[nome], espacamento,
        num_faixas=10, remocao_vegetal=remocao_vegetal,
        categoria=categoria_solo,
    )
    resultado_brk = construir_diagrama_bruckner(
        faixas,
        fator_empolamento=obter_fator_empolamento(categoria_solo),
        fator_homogeneizacao=obter_fator_homogeneizacao(categoria_solo),
    )
    fig = plotar_bruckner(resultado_brk)
    st.plotly_chart(fig, use_container_width=True)

    b1, b2, b3 = st.columns(3)
    b1.metric("DMT", f"{resultado_brk.dmt:,.1f} m")
    b2.metric("Bota-fora", f"{resultado_brk.volume_bota_fora:,.1f} m\u00b3")
    b3.metric("Solo Importado", f"{resultado_brk.volume_solo_importado:,.1f} m\u00b3")

with tab_tabela:
    fig_tabela = criar_tabela_volumes(lista_resultados)
    st.plotly_chart(fig_tabela, use_container_width=True)

    fig_barras = criar_grafico_barras_volumes(lista_resultados)
    st.plotly_chart(fig_barras, use_container_width=True)

    # DataFrame detalhado
    df_detalhe = pd.DataFrame([
        {
            "Pol\u00edgono": r.nome_poligono,
            "Cota (m)": r.cota_projeto,
            "\u00c1rea (m\u00b2)": r.area_total,
            "Corte Bruto (m\u00b3)": r.volume_corte_bruto,
            "Aterro Bruto (m\u00b3)": r.volume_aterro_bruto,
            "Corte Empolado (m\u00b3)": r.volume_corte_empolado,
            "Aterro Compactado (m\u00b3)": r.volume_aterro_compactado,
            "Bota-fora (m\u00b3)": r.volume_bota_fora,
            "Solo Importado (m\u00b3)": r.volume_solo_importado,
            "Balan\u00e7o (m\u00b3)": r.balanco_massa,
        }
        for r in lista_resultados
    ])
    st.dataframe(df_detalhe, use_container_width=True)


# ─── Tab Downloads ───
with tab_download:
    st.subheader("\U0001f4e5 Exportar Relat\u00f3rios")

    # Coleta figuras para relatorio analitico
    figuras_relatorio = {}
    for nome in nomes_poly:
        figuras_relatorio[f"Curvas de N\u00edvel - {nome}"] = criar_mapa_contorno(
            superficies[nome], titulo=f"Curvas de N\u00edvel - {nome}",
        )
        figuras_relatorio[f"Corte/Aterro - {nome}"] = criar_mapa_corte_aterro(
            superficies[nome], cotas[nome], remocao_vegetal,
        )
        figuras_relatorio[f"3D Terreno - {nome}"] = criar_superficie_3d(
            superficies[nome], grades[nome],
        )
        figuras_relatorio[f"3D Compara\u00e7\u00e3o - {nome}"] = criar_comparacao_3d(
            superficies[nome], cotas[nome], remocao_vegetal,
        )

    figuras_relatorio["Volumes por Pol\u00edgono"] = criar_grafico_barras_volumes(lista_resultados)

    relatorios = gerar_relatorio_html(lista_resultados, figuras_relatorio, parametros)

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
        # Aba resumo
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
            for r in lista_resultados
        ])
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)

        # Aba faixas por poligono
        todas_faixas = []
        for nome in nomes_poly:
            faixas = calcular_volumes_por_faixas(
                superficies[nome], cotas[nome], espacamento,
                num_faixas=10, remocao_vegetal=remocao_vegetal,
                categoria=categoria_solo,
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
