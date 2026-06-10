"""Pagina: Terreno 3D - Greide de projeto com taludes (daylight por inclinacao local)."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.greide import (
    amostrar_contorno, resolver_taludes, varredura_cota, volumes_internos,
)
from modulos.parametros import premissa_taludes_md
from modulos.visualizacao import criar_greide_3d

pagina_requer_dados()
dados = obter_dados()

st.subheader("Terreno 3D — Greide e taludes")

nome = seletor_poligono("3d")

superficie = dados["superficies"][nome]
grade = dados["grades"][nome]
p = dados["parametros"]
cota_ref = float(dados["cotas"].get(nome))

r_corte = p.talude_corte_h / p.talude_corte_v
r_aterro = p.talude_aterro_h / p.talude_aterro_v
remocao = getattr(p, "remocao_vegetal", 0.0) or 0.0

col1, col2 = st.columns(2)
with col1:
    cota = st.number_input(
        "Cota do platô (m)", value=round(cota_ref, 2), step=0.25, format="%.2f",
        key="cota_greide",
    )
with col2:
    exagero = st.select_slider(
        "Exagero vertical", options=[1, 2, 3, 4, 5], value=1, key="exagero_3d",
    )

st.info(
    premissa_taludes_md(p) + ". O *daylight* (linha pontilhada) é onde o "
    "talude morre no terreno natural extrapolado pela inclinação local — pode "
    "invadir além da divisa."
)

# Motor: contorno (independe da cota — cacheado para a cota responder
# instantaneamente) + resolucao dos taludes
_chave_contorno = (nome, st.session_state.get("dados_versao", 0), round(remocao, 6))
_cache_contorno = st.session_state.get("_contorno_cache")
if _cache_contorno is not None and _cache_contorno[0] == _chave_contorno:
    contorno = _cache_contorno[1]
else:
    contorno = amostrar_contorno(grade, superficie, remocao_vegetal=remocao)
    st.session_state["_contorno_cache"] = (_chave_contorno, contorno)
tal = resolver_taludes(contorno, cota, r_corte, r_aterro)

fig = criar_greide_3d(
    superficie, grade, tal, cota_projeto=cota,
    titulo="Greide — {}".format(nome), exagero_vertical=exagero,
)
st.plotly_chart(fig, width="stretch")

# ── Metricas: footprint e volumes (interno + talude) ──
ci, ai = volumes_internos(superficie, cota, grade.espacamento, remocao)

m = st.columns(4)
m[0].metric("Área invadida além da divisa", "{:,.0f} m²".format(tal.area_footprint))
m[1].metric("Corte total (lote + talude)", "{:,.0f} m³".format(ci + tal.volume_corte),
            help="Interno {:,.0f} + talude {:,.0f} m³".format(ci, tal.volume_corte))
m[2].metric("Aterro total (lote + talude)", "{:,.0f} m³".format(ai + tal.volume_aterro),
            help="Interno {:,.0f} + talude {:,.0f} m³".format(ai, tal.volume_aterro))
saldo = (ci + tal.volume_corte) - (ai + tal.volume_aterro)
m[3].metric("Saldo (corte − aterro)", "{:,.0f} m³".format(saldo),
            help="Positivo = sobra material; negativo = falta (importar).")

if tal.incompleto.any():
    st.warning(
        "{} estações de talude não encontraram o terreno (o talude é mais raso "
        "que o caimento natural) e foram limitadas. Reveja a inclinação ou "
        "considere muro de arrimo nesses trechos.".format(int(tal.incompleto.sum()))
    )

# ── Varredura: cota otima ──
with st.expander("Cota ótima do platô (varredura)", expanded=False):
    faixa = st.slider(
        "Faixa de cotas a varrer (m)",
        float(superficie.elevacao_min), float(superficie.elevacao_max),
        (float(superficie.elevacao_min), float(superficie.elevacao_max)),
        key="faixa_cota",
    )
    cotas = np.linspace(faixa[0], faixa[1], 30)
    vr = varredura_cota(contorno, superficie, grade.espacamento, cotas,
                        r_corte, r_aterro, remocao)

    figv = go.Figure()
    figv.add_trace(go.Scatter(x=vr["cotas"], y=vr["corte_total"],
                              name="Corte total", line=dict(color="#e07b54")))
    figv.add_trace(go.Scatter(x=vr["cotas"], y=vr["aterro_total"],
                              name="Aterro total", line=dict(color="#5b9bd5")))
    figv.add_trace(go.Scatter(x=vr["cotas"], y=vr["total"],
                              name="Volume total movimentado",
                              line=dict(color="#444", dash="dash")))
    figv.add_vline(x=vr["cota_min_total"], line=dict(color="green", dash="dot"))
    figv.add_vline(x=vr["cota_equilibrio"], line=dict(color="purple", dash="dot"))
    figv.update_layout(
        template="plotly_white", height=380,
        xaxis_title="Cota do platô (m)", yaxis_title="Volume (m³)",
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=40, r=20, b=40, t=30),
    )
    st.plotly_chart(figv, width="stretch")
    c1, c2 = st.columns(2)
    c1.metric("Cota de menor volume total", "{:.2f} m".format(vr["cota_min_total"]))
    c2.metric("Cota de equilíbrio corte≈aterro", "{:.2f} m".format(vr["cota_equilibrio"]))
    st.caption(
        "Inclui o volume escondido nos taludes. A cota de equilíbrio minimiza "
        "transporte (corte ≈ aterro); a de menor volume minimiza terra movimentada."
    )
