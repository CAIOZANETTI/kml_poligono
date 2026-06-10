"""Pagina: Conceito - o plano de projeto e a geracao de corte e aterro."""

import streamlit as st
from modulos.estado import carregar_dados_sessao

st.subheader("Conceito: o plano de projeto")

st.markdown(
    "Terraplenagem e, no fundo, **encaixar um plano dentro de um terreno**. "
    "O terreno natural e irregular; a obra precisa de uma superficie de apoio "
    "regular — uma **plataforma** numa altura definida, a **cota de projeto**. "
    "Tudo o que o sistema calcula nasce do encontro entre esses dois elementos: "
    "o **terreno** (o que existe) e o **plano** (o que se quer)."
)

# ── 1. O plano corta o terreno ──
st.markdown("---")
st.markdown("#### 1. O plano corta o terreno")
st.markdown(
    "Imagine uma folha horizontal atravessando o relevo na cota de projeto. "
    "Em cada ponto do lote comparamos a altura do terreno com a altura do plano:"
)
st.latex(r"\Delta h = C_{projeto} - T_{terreno}")
st.markdown(
    "- $\\Delta h < 0$ &rarr; o terreno esta **acima** do plano: sobra material, "
    "e preciso **CORTAR** (vermelho).  \n"
    "- $\\Delta h > 0$ &rarr; o terreno esta **abaixo** do plano: falta material, "
    "e preciso **ATERRAR** (azul).  \n"
    "- $\\Delta h = 0$ &rarr; terreno e plano se tocam: e a **linha de interseccao**, "
    "a divisa natural entre corte e aterro (a linha preta no Terreno 3D)."
)

# ── 2. Da diferenca ao volume ──
st.markdown("---")
st.markdown("#### 2. Da diferenca de altura ao volume")
st.markdown(
    "O lote e coberto por uma grade de celulas quadradas. Em cada celula a "
    "diferenca de altura vira um pequeno prisma; somando todos os prismas "
    "chega-se aos volumes totais de corte e de aterro (metodo da grade, DNIT)."
)
st.latex(r"V = \sum_i \Delta h_i \times A_{celula}")

# ── 3. Onde colocar o plano ──
st.markdown("---")
st.markdown("#### 3. Onde colocar o plano?")
st.markdown(
    "Subir a cota gera mais aterro e menos corte; baixar faz o contrario. "
    "A **cota otima** e a altura em que o corte iguala o aterro — o "
    "**balanco** fica perto de zero e a obra quase nao importa nem descarta "
    "terra. Quando sobra material vira **bota-fora**; quando falta, vira "
    "**solo importado** (emprestimo)."
)

# ── 4. Volumes geometricos ──
st.markdown("---")
st.markdown("#### 4. Os volumes sao geometricos (in-situ)")
st.markdown(
    "Todos os volumes desta analise sao medidos **na geometria do terreno** "
    "(in-situ): quanto espaco o corte ocupa e quanto vazio o aterro preenche. "
    "Na obra, 1 m3 escavado nao vira exatamente 1 m3 de aterro — solo "
    "escavado incha (empolamento) e, compactado, encolhe; rocha detonada "
    "ocupa mais volume. Essas conversoes dependem do **material real de cada "
    "trecho** (solo, rocha alterada, rocha, misturas) e por isso pertencem a "
    "uma **analise de materiais separada**, feita com sondagens e ensaios."
)

# ── 5. Como ler cada tela ──
st.markdown("---")
st.markdown("#### 5. Como ler cada visualizacao")
st.markdown(
    "- **Curvas de nivel** — o terreno em planta; a linha vermelha e a "
    "interseccao com a cota de projeto (a divisa corte/aterro vista de cima).  \n"
    "- **Terreno 3D** — o relevo real colorido por corte (vermelho) e aterro "
    "(azul); o plano cinza e a plataforma e a linha preta e onde ele corta o "
    "terreno.  \n"
    "- **Corte e Aterro 3D** — os volumes solidos: vermelho sobe acima do "
    "plano (material a remover), azul preenche por baixo ate o plano (material "
    "a colocar).  \n"
    "- **Bruckner** — o transporte: quanto material anda e para onde, ao longo "
    "do eixo da obra.  \n"
    "- **Memoria de Calculo** — todas as formulas com os numeros do projeto."
)

# ── Estado atual, se houver dados ──
dados = carregar_dados_sessao()
if dados:
    st.markdown("---")
    st.markdown("#### Neste projeto")
    cols = st.columns(len(dados["cotas"]) or 1)
    for col, (nome, cota) in zip(cols, dados["cotas"].items()):
        res = dados["resultados"].get(nome)
        balanco = res.balanco_massa if res else 0.0
        situacao = "bota-fora" if balanco > 0 else ("solo importado" if balanco < 0 else "equilibrio")
        col.metric(
            "{} — cota".format(nome), "{:.2f} m".format(cota),
            delta=situacao, delta_color="off",
        )
else:
    st.info("Faca upload de um KML na Home para ver os numeros do seu projeto aqui.")

st.markdown("---")
st.caption(
    "Ref.: DNIT 106/2009-ES (Cortes) | DNIT 108/2009-ES (Aterros) | "
    "DER/PR Manual de Terraplenagem 2023"
)
