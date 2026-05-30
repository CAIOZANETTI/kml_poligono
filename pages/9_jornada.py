"""Pagina: Jornada de desenvolvimento - como este MVP foi construido com IA.

Os numeros sao um retrato do historico do repositorio (commits, PRs e
linhas de codigo), embutidos estaticamente para nao depender de rede.
"""

import plotly.graph_objects as go
import streamlit as st

from modulos.tema import CORES

# ── Dados do historico (git) ──
# (data, commits, PRs mesclados, linhas adicionadas, linhas removidas)
DIAS = [
    ("2026-03-26", 19, 7, 4235, 661),
    ("2026-03-27", 33, 14, 1941, 1293),
    ("2026-03-30", 2, 1, 145, 1),
    ("2026-03-31", 8, 4, 515, 306),
    ("2026-05-01", 1, 0, 33, 0),
    ("2026-05-30", 5, 4, 594, 296),
]
PRS_MESCLADOS = 30
BRANCHES_FEATURE = 10
PERIODO = "26/mar a 30/mai de 2026"

# ── Investimento (ajustaveis) ──
# Preencha com os valores reais da sua jornada.
HORAS_DEV = 30          # horas de desenvolvimento assistido por IA
CUSTO_USD = None        # custo total em US$ (None oculta o card)

total_commits = sum(d[1] for d in DIAS)
total_add = sum(d[3] for d in DIAS)
total_del = sum(d[4] for d in DIAS)
dias_ativos = len(DIAS)

st.subheader("Jornada de desenvolvimento")
st.caption("como um MVP de engenharia nasceu em parceria com o Claude Code")

# ── Narrativa ──
st.markdown(
    "Esta ferramenta nao foi escrita de uma vez. Ela **evoluiu em ciclos "
    "curtos**: uma ideia virava um pedido, o Claude Code abria um branch, "
    "propunha o codigo, a gente revisava, mesclava e seguia para o proximo "
    "ajuste. Cada melhoria que voce ve no app — do calculo de volumes as "
    "visualizacoes 3D — e o acumulo de dezenas dessas pequenas voltas."
)
st.markdown(
    "O resultado e um retrato concreto do que e desenvolver um **MVP com "
    "inteligencia artificial**: rapido para experimentar, barato para errar "
    "e refazer, e documentado a cada passo pelos proprios commits e pull "
    "requests."
)

# ── Numeros da jornada ──
st.markdown("---")
st.markdown("#### Os numeros da jornada")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Commits", "{}".format(total_commits))
c2.metric("Pull requests", "{}".format(PRS_MESCLADOS))
c3.metric("Linhas de codigo", "+{:,}".format(total_add), delta="-{:,}".format(total_del), delta_color="off")
c4.metric("Frentes de trabalho", "{}".format(BRANCHES_FEATURE), delta=PERIODO, delta_color="off")

ci1, ci2 = st.columns(2)
ci1.metric("Horas de desenvolvimento", "~{} h".format(HORAS_DEV))
if CUSTO_USD is not None:
    ci2.metric("Custo total", "US$ {:,.0f}".format(CUSTO_USD))
else:
    ci2.metric("Custo por entrega", "fracao de uma hora de engenharia")

# ── Grafico: atividade ao longo do tempo ──
st.markdown("---")
st.markdown("#### Atividade ao longo do tempo")
datas = [d[0] for d in DIAS]
commits = [d[1] for d in DIAS]
adicionadas = [d[3] for d in DIAS]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=datas, y=commits, name="Commits",
    marker_color=CORES["accent"], yaxis="y",
))
fig.add_trace(go.Scatter(
    x=datas, y=adicionadas, name="Linhas adicionadas",
    mode="lines+markers", line=dict(color=CORES["corte"], width=2), yaxis="y2",
))
fig.update_layout(
    template="plotly_white",
    height=380,
    margin=dict(l=40, r=40, b=40, t=20),
    yaxis=dict(title="Commits"),
    yaxis2=dict(title="Linhas +", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", y=1.12, x=0),
)
st.plotly_chart(fig, use_container_width=True)

# ── Fases ──
st.markdown("---")
st.markdown("#### As fases do MVP")
st.markdown(
    "- **Fundacao** — leitura de KML, conversao UTM e geracao da grade.  \n"
    "- **Calculo de volumes** — metodo da grade (DNIT), corte/aterro, cota "
    "otima e fatores de empolamento.  \n"
    "- **Visualizacoes** — curvas de nivel, terreno 3D e solidos de corte e "
    "aterro.  \n"
    "- **Relatorios** — HTML gerencial/analitico e planilha de exportacao.  \n"
    "- **Auditoria de UX** — relevo real, plataforma de projeto, indicacao de "
    "norte, metricas compactas e esta narrativa.  \n"
    "- **Conceito e memoria** — paginas que explicam o metodo, nao so os "
    "numeros."
)

st.markdown("---")
st.caption(
    "Historico extraido dos commits e pull requests do repositorio "
    "CAIOZANETTI/kml_poligono. Desenvolvimento assistido por Claude Code."
)
