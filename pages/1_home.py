"""Pagina inicial - Configuracao de poligonos e metricas."""

import streamlit as st
from modulos.estado import processar_poligonos, obter_dados
from modulos.volumes import calcular_cota_otima, calcular_volumes

st.title("\U0001f3d7\ufe0f Terraplenagem - C\u00e1lculo de Volumes")
st.caption("Importe pol\u00edgonos KML do Google Earth para calcular corte e aterro")

if not processar_poligonos():
    st.info("\U0001f446 Fa\u00e7a upload de arquivos KML na barra lateral para come\u00e7ar.")
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
st.header("\U0001f4cd Pol\u00edgonos Carregados ({})".format(len(poligonos)))

for poly in poligonos:
    nome = poly.nome
    grade = grades[nome]
    superficie = superficies[nome]

    with st.expander("\U0001f4d0 {}".format(nome), expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pontos", len(poly.pontos))
        c2.metric("\u00c1rea", "{:,.0f} m\u00b2".format(grade.area))
        c3.metric("Per\u00edmetro", "{:,.0f} m".format(grade.perimetro))
        c4.metric("Elev. M\u00edn", "{:.2f} m".format(superficie.elevacao_min))
        c5.metric("Elev. M\u00e1x", "{:.2f} m".format(superficie.elevacao_max))

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
                "Cota \u00f3tima",
                key="otima_{}".format(nome),
                help="Calcula a cota onde corte = aterro",
            )

        if usar_cota_otima:
            cota_ot, res_ot = calcular_cota_otima(
                superficie, espacamento, remocao_vegetal,
                categoria_solo, nome_poligono=nome,
            )
            st.success("Cota \u00f3tima: **{:.2f} m** (balan\u00e7o: {:.2f} m\u00b3)".format(
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

# Atualiza session_state
st.session_state["resultados"] = resultados
st.session_state["cotas"] = cotas

# ─── Metricas resumo ───
st.divider()
lista_res = list(resultados.values())

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Total Corte Empolado", "{:,.1f} m\u00b3".format(
    sum(r.volume_corte_empolado for r in lista_res)))
mc2.metric("Total Aterro Compactado", "{:,.1f} m\u00b3".format(
    sum(r.volume_aterro_compactado for r in lista_res)))
mc3.metric("Bota-fora", "{:,.1f} m\u00b3".format(
    sum(r.volume_bota_fora for r in lista_res)))
mc4.metric("Solo Importado", "{:,.1f} m\u00b3".format(
    sum(r.volume_solo_importado for r in lista_res)))
