"""Pagina inicial - Upload, parametros, configuracao de poligonos e metricas."""

import math
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


def _fmt_area(m2: float) -> str:
    """Area compacta em hectares."""
    return "{:,.2f} ha".format(m2 / 10_000)


def _fmt_vol(m3: float) -> str:
    """Volume compacto: M m3 / mil m3 / m3 conforme a grandeza."""
    a = abs(m3)
    if a >= 1e6:
        return "{:,.2f} M m³".format(m3 / 1e6)
    if a >= 1e3:
        return "{:,.1f} mil m³".format(m3 / 1e3)
    return "{:,.0f} m³".format(m3)

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
st.caption(
    "Inclina\u00e7\u00e3o na conven\u00e7\u00e3o **1:N** (1 vertical para N horizontal). "
    "A vertical \u00e9 fixa em 1 \u2014 escolha o padr\u00e3o ou personalize."
)


def _rotulo_talude(razao: float) -> str:
    """Rotulo '1:N (\u00e2ngulo\u00b0)' a partir da razao H/V (V=1)."""
    ang = math.degrees(math.atan(1.0 / razao))
    n = ("%g" % razao).replace(".", ",")
    return "1:{} ({:.1f}\u00b0)".format(n, ang)


_PRESETS_CORTE = [0.5, 1.0, 1.5, 2.0]    # taludes mais ingremes (corte)
_PRESETS_ATERRO = [1.5, 2.0, 2.5, 3.0]   # taludes mais suaves (aterro)
_PERSONALIZADO = "Personalizado\u2026"

col_tc, col_ta = st.columns(2)
with col_tc:
    opts_c = [_rotulo_talude(r) for r in _PRESETS_CORTE] + [_PERSONALIZADO]
    sel_c = st.selectbox("Talude de corte", opts_c, index=1)  # 1:1 (45\u00b0)
    if sel_c == _PERSONALIZADO:
        talude_corte_h = st.number_input(
            "Corte \u2014 N (horizontal para 1 vertical)",
            value=1.0, min_value=0.1, step=0.25, key="corte_custom",
        )
    else:
        talude_corte_h = _PRESETS_CORTE[opts_c.index(sel_c)]
    talude_corte_v = 1.0
with col_ta:
    opts_a = [_rotulo_talude(r) for r in _PRESETS_ATERRO] + [_PERSONALIZADO]
    sel_a = st.selectbox("Talude de aterro", opts_a, index=1)  # 1:2 (26,6\u00b0)
    if sel_a == _PERSONALIZADO:
        talude_aterro_h = st.number_input(
            "Aterro \u2014 N (horizontal para 1 vertical)",
            value=2.0, min_value=0.1, step=0.25, key="aterro_custom",
        )
    else:
        talude_aterro_h = _PRESETS_ATERRO[opts_a.index(sel_a)]
    talude_aterro_v = 1.0

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
                talude_corte_h=parametros.talude_corte_h,
                talude_corte_v=parametros.talude_corte_v,
                talude_aterro_h=parametros.talude_aterro_h,
                talude_aterro_v=parametros.talude_aterro_v,
                grade=grade,
            )

        # Metricas principais (4 por linha, formato compacto)
        res = resultados[nome]
        balanco_poly = res.volume_corte_empolado - res.volume_aterro_compactado

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Area", _fmt_area(grade.area))
        c2.metric(
            "Corte", _fmt_vol(res.volume_corte_empolado),
            delta="empolado", delta_color="off",
        )
        c3.metric(
            "Aterro", _fmt_vol(res.volume_aterro_compactado),
            delta="compactado", delta_color="off",
        )
        c4.metric(
            "Balanco", _fmt_vol(balanco_poly),
            delta="bota-fora" if balanco_poly > 0 else "solo importado",
            delta_color="inverse",
        )

        # Detalhes secundarios fora do caminho principal
        with st.expander("detalhes"):
            d1, d2, d3 = st.columns(3)
            d1.metric("Perimetro", "{:,.0f} m".format(grade.perimetro))
            d1.metric("Elev. min / max", "{:.1f} / {:.1f} m".format(
                superficie.elevacao_min, superficie.elevacao_max,
            ))
            d2.metric("Corte bruto", _fmt_vol(res.volume_corte_bruto))
            d2.metric("Aterro bruto", _fmt_vol(res.volume_aterro_bruto))
            d3.metric("Remocao vegetal", _fmt_vol(res.volume_remocao_vegetal))
            d3.metric("Espessura remocao", "{:.2f} m".format(res.remocao_vegetal))

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
total_remocao = sum(r.volume_remocao_vegetal for r in lista_res)
balanco = total_corte - total_aterro

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric(
    "Corte empolado", _fmt_vol(total_corte),
    delta="{} poligonos".format(len(lista_res)), delta_color="off",
)
mc2.metric("Aterro compactado", _fmt_vol(total_aterro))
mc3.metric(
    "Balanco", _fmt_vol(balanco),
    delta="bota-fora" if balanco > 0 else ("solo importado" if balanco < 0 else "equilibrio"),
    delta_color="inverse",
)
mc4.metric(
    "Remocao vegetal", _fmt_vol(total_remocao),
    delta="bota-fora direto", delta_color="off",
)
