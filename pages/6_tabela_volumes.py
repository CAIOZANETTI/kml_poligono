"""Pagina: Memoria de Calculo de Volumes."""

import streamlit as st
from modulos.estado import pagina_requer_dados, obter_dados, seletor_poligono
from modulos.parametros import NOMES_CATEGORIA, FATORES_DNIT, _resolver_categoria

pagina_requer_dados()
dados = obter_dados()

st.subheader("Memoria de Calculo")

nome = seletor_poligono("vol")
r = dados["resultados"][nome]
cat = _resolver_categoria(r.categoria_solo)
fatores = FATORES_DNIT[cat]
nome_cat = NOMES_CATEGORIA[cat]
esp = dados["espacamento"]
a_cel = esp ** 2

# ── 1. Dados de entrada ──
st.markdown(
    "Esta memoria reconstroi, passo a passo, como se chega aos volumes de "
    "corte e aterro do poligono. A ideia central e simples: comparamos o "
    "**terreno natural** com a **plataforma de projeto** (um plano na cota "
    "desejada) e medimos, celula a celula, quanto material falta ou sobra."
)
st.markdown("---")
st.markdown("#### 1. Dados de entrada")
st.markdown(
    "Sao os parametros que definem o problema: a cota onde se quer a "
    "plataforma, a geometria do lote e os fatores de solo que corrigem os "
    "volumes. Tudo o que vem depois deriva destes valores."
)
st.markdown(
    "Poligono: **{nome}**  \n"
    "Cota de projeto: **Cp = {cota:.2f} m**  \n"
    "Elevacao media do terreno: **Tm = {elev:.2f} m**  \n"
    "Area total: **A = {area:,.2f} m\u00b2**  \n"
    "Espacamento da grade: **e = {esp:.2f} m**  \n"
    "Remocao vegetal: **rv = {rv:.2f} m**  \n"
    "Categoria de solo: **{cat}**  \n"
    "Fator de empolamento: **fe = {fe}**  \n"
    "Fator de homogeneizacao: **fh = {fh}**".format(
        nome=r.nome_poligono,
        cota=r.cota_projeto,
        elev=r.elevacao_media_terreno,
        area=r.area_total,
        esp=esp,
        rv=r.remocao_vegetal,
        cat=nome_cat,
        fe=fatores.empolamento,
        fh=fatores.homogeneizacao,
    )
)

# ── 2. Area da celula ──
st.markdown("---")
st.markdown("#### 2. Area da celula")
st.markdown(
    "O metodo da grade (DNIT) cobre o lote com uma malha de pontos igualmente "
    "espacados. Cada ponto representa uma celula quadrada de lado igual ao "
    "espacamento — e a unidade elementar de area sobre a qual mediremos altura "
    "e, depois, volume. Malhas mais finas dao mais precisao e mais celulas."
)
st.latex(r"A_{cel} = e^2 = %.2f^2 = %.2f \; m^2" % (esp, a_cel))

# ── 3. Remocao vegetal ──
st.markdown("---")
st.markdown("#### 3. Remocao vegetal")
st.markdown(
    "Antes de qualquer terraplenagem retira-se a camada organica de superficie "
    "(raizes e materia vegetal), que nao serve de apoio estrutural. Esse "
    "material vai direto para bota-fora e, por isso, a cota do terreno usada "
    "nos calculos e rebaixada nessa espessura antes de comparar com o projeto."
)
st.latex(r"V_{rv} = A \times rv = %.2f \times %.2f = %.2f \; m^3"
         % (r.area_total, r.remocao_vegetal, r.volume_remocao_vegetal))

# ── 4. Alturas relativas ──
st.markdown("---")
st.markdown("#### 4. Alturas relativas")
st.markdown(
    "Aqui o plano de projeto encontra o terreno. Em cada celula calculamos a "
    "distancia vertical entre a cota de projeto e o terreno ja limpo. O sinal "
    "dessa diferenca diz a natureza do servico naquele ponto:"
)
st.latex(r"\Delta h_i = C_p - (T_{n_i} - rv)")
st.markdown(
    "$\\Delta h > 0$ &rarr; o terreno esta **abaixo** do plano: falta material &rarr; **ATERRO**  \n"
    "$\\Delta h < 0$ &rarr; o terreno esta **acima** do plano: sobra material &rarr; **CORTE**  \n"
    "$\\Delta h = 0$ &rarr; terreno e plano se tocam: a **linha de interseccao**, "
    "fronteira entre as duas regioes."
)

# ── 5. Volume bruto de corte ──
st.markdown("---")
st.markdown("#### 5. Volume bruto de corte")
st.markdown(
    "Cada celula de corte vira um prisma: a base e a area da celula e a altura "
    "e o $|\\Delta h|$ daquele ponto. Somando todos os prismas onde o terreno "
    "esta acima do plano obtem-se o volume **bruto** (in-situ, antes de "
    "qualquer correcao). O talude de corte adiciona o material das bordas "
    "inclinadas que estabilizam a escavacao."
)
st.latex(r"V_{corte}^{bruto} = \sum_{i \in corte} |\Delta h_i| \times A_{cel}")
v_corte_grade = r.volume_corte_bruto - r.volume_talude_corte
st.latex(r"V_{corte}^{bruto} = %.2f \; m^3" % v_corte_grade)
if r.volume_talude_corte > 0:
    st.markdown("Com talude de corte:")
    st.latex(r"V_{corte}^{total} = %.2f + %.2f = %.2f \; m^3"
             % (v_corte_grade, r.volume_talude_corte, r.volume_corte_bruto))

st.latex(r"A_{corte} = %.2f \; m^2" % r.area_corte)

# ── 6. Volume bruto de aterro ──
st.markdown("---")
st.markdown("#### 6. Volume bruto de aterro")
st.markdown(
    "Mesmo raciocinio, agora nas celulas onde falta material: cada prisma "
    "representa o vazio entre o terreno e o plano, que sera preenchido. O "
    "talude de aterro contabiliza o material extra das saias inclinadas que "
    "sustentam o corpo do aterro nas bordas."
)
st.latex(r"V_{aterro}^{bruto} = \sum_{i \in aterro} \Delta h_i \times A_{cel}")
v_aterro_grade = r.volume_aterro_bruto - r.volume_talude_aterro
st.latex(r"V_{aterro}^{bruto} = %.2f \; m^3" % v_aterro_grade)
if r.volume_talude_aterro > 0:
    st.markdown("Com talude de aterro:")
    st.latex(r"V_{aterro}^{total} = %.2f + %.2f = %.2f \; m^3"
             % (v_aterro_grade, r.volume_talude_aterro, r.volume_aterro_bruto))

st.latex(r"A_{aterro} = %.2f \; m^2" % r.area_aterro)

# ── 7. Fatores DNIT ──
st.markdown("---")
st.markdown("#### 7. Fatores DNIT")
st.markdown(
    "Um metro cubico escavado nao vira um metro cubico de aterro. Ao ser "
    "removido, o solo se solta e **incha** (empolamento); ao ser lancado e "
    "compactado no aterro, ele **encolhe** (homogeneizacao). Para comparar "
    "corte e aterro em pe de igualdade, aplicamos os fatores DNIT da categoria "
    "do solo (**{cat}**) e passamos do volume geometrico para o volume real "
    "de obra.".format(cat=nome_cat)
)

st.markdown("Corte empolado (DNIT 106/2009-ES):")
st.latex(r"V_{corte}^{emp} = V_{corte}^{bruto} \times f_e = %.2f \times %.2f = %.2f \; m^3"
         % (r.volume_corte_bruto, fatores.empolamento, r.volume_corte_empolado))

st.markdown("Aterro compactado (DNIT 108/2009-ES):")
st.latex(r"V_{aterro}^{comp} = V_{aterro}^{bruto} \times f_h = %.2f \times %.2f = %.2f \; m^3"
         % (r.volume_aterro_bruto, fatores.homogeneizacao, r.volume_aterro_compactado))

# ── 8. Balanco de massa ──
st.markdown("---")
st.markdown("#### 8. Balanco de massa")
st.markdown(
    "O balanco confronta o que sai (corte empolado) com o que entra (aterro "
    "compactado) e responde a pergunta economica da obra: o material do proprio "
    "lote sobra, falta ou se equilibra? Subir a cota aumenta o aterro e reduz o "
    "corte; a **cota otima** e aquela em que o balanco se aproxima de zero \u2014 a "
    "terra do corte alimenta o aterro sem transporte externo."
)
st.latex(r"B = V_{corte}^{emp} - V_{aterro}^{comp} = %.2f - %.2f = %.2f \; m^3"
         % (r.volume_corte_empolado, r.volume_aterro_compactado, r.balanco_massa))

if r.balanco_massa > 0:
    st.markdown(
        "Balanco **positivo**: o corte gera mais material do que o aterro "
        "consome; o excedente vai para fora &rarr; **Bota-fora = %.2f m\u00b3**." % r.volume_bota_fora
    )
elif r.balanco_massa < 0:
    st.markdown(
        "Balanco **negativo**: o aterro pede mais material do que o corte "
        "fornece; a diferenca vem de jazida &rarr; **Solo importado = %.2f m\u00b3**." % r.volume_solo_importado
    )
else:
    st.markdown(
        "Balanco **equilibrado**: corte e aterro se compensam \u2014 sem bota-fora "
        "nem emprestimo."
    )

# ── Referencias ──
st.markdown("---")
st.caption(
    "Ref.: DNIT 106/2009-ES (Cortes) | "
    "DNIT 108/2009-ES (Aterros) | "
    "DNIT 381/2022-PRO"
)
