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
st.markdown("---")
st.markdown("#### 1. Dados de entrada")
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
st.latex(r"A_{cel} = e^2 = %.2f^2 = %.2f \; m^2" % (esp, a_cel))

# ── 3. Remocao vegetal ──
st.markdown("---")
st.markdown("#### 3. Remocao vegetal")
st.latex(r"V_{rv} = A \times rv = %.2f \times %.2f = %.2f \; m^3"
         % (r.area_total, r.remocao_vegetal, r.volume_remocao_vegetal))

# ── 4. Alturas relativas ──
st.markdown("---")
st.markdown("#### 4. Alturas relativas")
st.latex(r"\Delta h_i = C_p - (T_{n_i} - rv)")
st.markdown(
    "$\\Delta h > 0$ &rarr; ATERRO  \n"
    "$\\Delta h < 0$ &rarr; CORTE"
)

# ── 5. Volume bruto de corte ──
st.markdown("---")
st.markdown("#### 5. Volume bruto de corte")
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

st.markdown("Corte empolado (DNIT 106/2009-ES):")
st.latex(r"V_{corte}^{emp} = V_{corte}^{bruto} \times f_e = %.2f \times %.2f = %.2f \; m^3"
         % (r.volume_corte_bruto, fatores.empolamento, r.volume_corte_empolado))

st.markdown("Aterro compactado (DNIT 108/2009-ES):")
st.latex(r"V_{aterro}^{comp} = V_{aterro}^{bruto} \times f_h = %.2f \times %.2f = %.2f \; m^3"
         % (r.volume_aterro_bruto, fatores.homogeneizacao, r.volume_aterro_compactado))

# ── 8. Balanco de massa ──
st.markdown("---")
st.markdown("#### 8. Balanco de massa")
st.latex(r"B = V_{corte}^{emp} - V_{aterro}^{comp} = %.2f - %.2f = %.2f \; m^3"
         % (r.volume_corte_empolado, r.volume_aterro_compactado, r.balanco_massa))

if r.balanco_massa > 0:
    st.markdown("Excesso de material &rarr; **Bota-fora = %.2f m\u00b3**" % r.volume_bota_fora)
elif r.balanco_massa < 0:
    st.markdown("Deficit de material &rarr; **Solo importado = %.2f m\u00b3**" % r.volume_solo_importado)
else:
    st.markdown("Balanco equilibrado.")

# ── Referencias ──
st.markdown("---")
st.caption(
    "Ref.: DNIT 106/2009-ES (Cortes) | "
    "DNIT 108/2009-ES (Aterros) | "
    "DNIT 381/2022-PRO"
)
