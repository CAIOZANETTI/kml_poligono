"""Pagina inicial - Upload, parametros, configuracao de poligonos e metricas."""

import streamlit as st
from modulos.estado import (
    processar_poligonos, obter_dados, salvar_dados_sessao,
    carregar_dados_sessao,
)
from modulos.volumes import calcular_cota_otima, calcular_volumes
from modulos.parametros import (
    ParametrosPadrao, CategoriaSolo, NOMES_CATEGORIA, FATORES_DNIT,
    _resolver_categoria,
)

st.title("Terraplenagem")
st.caption("importe poligonos kml do google earth para calcular corte e aterro")

# ─── Upload ───
st.subheader("Upload")
arquivos_kml = st.file_uploader(
    "Arquivos KML",
    type=["kml"],
    accept_multiple_files=True,
    help="Poligonos do Google Earth com elevacao",
)

# ─── Parametros ───
st.subheader("Parametros")

col_esp, col_rem = st.columns(2)
with col_esp:
    espacamento = st.number_input(
        "Espacamento da grade (m)",
        min_value=0.5, max_value=500.0, value=10.0, step=1.0,
        help="Distancia entre pontos internos da grade",
    )
with col_rem:
    remocao_vegetal = st.number_input(
        "Remocao vegetal (m)",
        min_value=0.0, max_value=2.0, value=0.30, step=0.05,
    )

col_cat, col_info = st.columns(2)
with col_cat:
    categoria_opcoes = {v: k for k, v in NOMES_CATEGORIA.items()}
    cat_selecionada = st.selectbox(
        "Categoria do solo",
        list(categoria_opcoes.keys()),
    )
    categoria_solo = categoria_opcoes[cat_selecionada]
with col_info:
    fatores = FATORES_DNIT[_resolver_categoria(categoria_solo)]
    st.write("")
    st.caption(
        "empolamento: {} · homogeneizacao: {}".format(
            fatores.empolamento, fatores.homogeneizacao
        )
    )

st.subheader("Taludes")
col_tc, col_ta = st.columns(2)
with col_tc:
    talude_corte_h = st.number_input("Corte H", value=1.0, min_value=0.1, step=0.5)
    talude_corte_v = st.number_input("Corte V", value=1.0, min_value=0.1, step=0.5)
with col_ta:
    talude_aterro_h = st.number_input("Aterro H", value=2.0, min_value=0.1, step=0.5)
    talude_aterro_v = st.number_input("Aterro V", value=1.0, min_value=0.1, step=0.5)

# Salva parametros no session_state
parametros = ParametrosPadrao(
    espacamento_grade=espacamento,
    remocao_vegetal=remocao_vegetal,
    talude_corte_h=talude_corte_h,
    talude_corte_v=talude_corte_v,
    talude_aterro_h=talude_aterro_h,
    talude_aterro_v=talude_aterro_v,
    categoria_solo=categoria_solo,
)
st.session_state["espacamento"] = espacamento
st.session_state["remocao_vegetal"] = remocao_vegetal
st.session_state["categoria_solo"] = categoria_solo
st.session_state["parametros"] = parametros

# ─── Processar arquivos ───
st.divider()

if arquivos_kml:
    novos_bytes = []
    for arq in arquivos_kml:
        conteudo = arq.read()
        arq.seek(0)
        novos_bytes.append((conteudo, arq.name))
    bytes_antigos = st.session_state.get("kml_bytes")
    nomes_novos = sorted([n for _, n in novos_bytes])
    nomes_antigos = sorted([n for _, n in bytes_antigos]) if bytes_antigos else []
    if nomes_novos != nomes_antigos:
        st.session_state.pop("dados_json", None)
    st.session_state["kml_bytes"] = novos_bytes

if not processar_poligonos():
    st.info("Faca upload de arquivos KML acima para comecar.")
    st.stop()

dados = obter_dados()
poligonos = dados["poligonos"]
grades = dados["grades"]
superficies = dados["superficies"]
resultados = dados["resultados"]
cotas = dados["cotas"]
espacamento = dados["espacamento"]
remocao_vegetal = dados["remocao_vegetal"]
categoria_solo = dados["categoria_solo"]

# ─── Poligonos Carregados ───
st.subheader("Poligonos carregados ({})".format(len(poligonos)))

for poly in poligonos:
    nome = poly.nome
    grade = grades[nome]
    superficie = superficies[nome]

    with st.expander(nome, expanded=True):
        # Cota do projeto
        col_cota, col_otima = st.columns([3, 1])
        with col_cota:
            cota_input = st.number_input(
                "Cota do projeto (m)",
                value=round(superficie.elevacao_media, 2),
                step=0.10,
                format="%.2f",
                key="cota_{}".format(nome),
            )
        with col_otima:
            st.write("")
            usar_cota_otima = st.checkbox(
                "Cota otima",
                key="otima_{}".format(nome),
                help="Calcula a cota onde corte = aterro",
            )

        if usar_cota_otima:
            cota_ot, res_ot = calcular_cota_otima(
                superficie, espacamento, remocao_vegetal,
                categoria_solo, nome_poligono=nome,
            )
            st.success("cota otima: **{:.2f} m** (balanco: {:.2f} m\u00b3)".format(
                cota_ot, res_ot.balanco_massa
            ))
            cotas[nome] = cota_ot
            resultados[nome] = res_ot
        else:
            cotas[nome] = cota_input
            resultados[nome] = calcular_volumes(
                superficie, cota_input, espacamento,
                remocao_vegetal, categoria_solo, nome,
            )

        # Metricas com delta
        cota_proj = cotas[nome]
        res = resultados[nome]
        amplitude = superficie.elevacao_max - superficie.elevacao_min

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(
            "Area",
            "{:,.0f} m\u00b2".format(grade.area),
            delta="{:,.0f} m perim.".format(grade.perimetro),
            delta_color="off",
        )
        c2.metric(
            "Elev. min",
            "{:.2f} m".format(superficie.elevacao_min),
            delta="{:.2f} m".format(superficie.elevacao_min - cota_proj),
        )
        c3.metric(
            "Elev. max",
            "{:.2f} m".format(superficie.elevacao_max),
            delta="{:.2f} m".format(superficie.elevacao_max - cota_proj),
        )
        c4.metric(
            "Corte",
            "{:,.1f} m\u00b3".format(res.volume_corte_empolado),
            delta="{:,.1f} m\u00b3 bruto".format(res.volume_corte_bruto),
            delta_color="off",
        )
        c5.metric(
            "Aterro",
            "{:,.1f} m\u00b3".format(res.volume_aterro_compactado),
            delta="{:,.1f} m\u00b3 bruto".format(res.volume_aterro_bruto),
            delta_color="off",
        )

salvar_dados_sessao(
    poligonos, grades, superficies, resultados, cotas,
    parametros, espacamento, remocao_vegetal, categoria_solo,
)

# ─── Resumo ───
st.divider()
st.subheader("Resumo")
lista_res = list(resultados.values())

total_corte = sum(r.volume_corte_empolado for r in lista_res)
total_aterro = sum(r.volume_aterro_compactado for r in lista_res)
total_bota = sum(r.volume_bota_fora for r in lista_res)
total_solo = sum(r.volume_solo_importado for r in lista_res)
balanco = total_corte - total_aterro

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric(
    "Corte empolado",
    "{:,.1f} m\u00b3".format(total_corte),
    delta="{:,.1f} m\u00b3 balanco".format(balanco),
    delta_color="off",
)
mc2.metric(
    "Aterro compactado",
    "{:,.1f} m\u00b3".format(total_aterro),
    delta="{} poligonos".format(len(lista_res)),
    delta_color="off",
)
mc3.metric(
    "Bota-fora",
    "{:,.1f} m\u00b3".format(total_bota),
    delta="excesso" if total_bota > 0 else "zero",
    delta_color="inverse" if total_bota > 0 else "off",
)
mc4.metric(
    "Solo importado",
    "{:,.1f} m\u00b3".format(total_solo),
    delta="deficit" if total_solo > 0 else "zero",
    delta_color="inverse" if total_solo > 0 else "off",
)
