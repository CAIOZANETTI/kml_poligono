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

# ── 1. Dados de entrada ──
st.markdown("---")
st.markdown("### 1. Dados de entrada")

st.markdown("""
| Parametro | Valor |
|:----------|------:|
| Poligono | **{nome}** |
| Cota de projeto (Cp) | **{cota:.2f} m** |
| Elevacao media do terreno (Tm) | **{elev_media:.2f} m** |
| Area total do poligono (A) | **{area:,.2f} m\u00b2** |
| Espacamento da grade (e) | **{esp:.2f} m** |
| Remocao vegetal (rv) | **{rv:.2f} m** |
| Categoria de solo | **{cat_nome}** |
| Fator de empolamento (fe) | **{fe:.2f}** |
| Fator de homogeneizacao (fh) | **{fh:.2f}** |
""".format(
    nome=r.nome_poligono,
    cota=r.cota_projeto,
    elev_media=r.elevacao_media_terreno,
    area=r.area_total,
    esp=dados["espacamento"],
    rv=r.remocao_vegetal,
    cat_nome=nome_cat,
    fe=fatores.empolamento,
    fh=fatores.homogeneizacao,
))

# ── 2. Area da celula ──
st.markdown("---")
st.markdown("### 2. Area da celula")

esp = dados["espacamento"]
a_cel = esp ** 2

st.latex(r"A_{cel} = e^2 = %.2f^2 = %.2f \; m^2" % (esp, a_cel))

# ── 3. Volume de remocao vegetal ──
st.markdown("---")
st.markdown("### 3. Volume de remocao vegetal")

st.markdown("Antes do calculo de volumes, remove-se a camada vegetal de toda a area:")

st.latex(r"V_{rv} = A \times rv")
st.latex(r"V_{rv} = %.2f \times %.2f" % (r.area_total, r.remocao_vegetal))
st.latex(r"V_{rv} = %.2f \; m^3" % r.volume_remocao_vegetal)

# ── 4. Calculo do delta ──
st.markdown("---")
st.markdown("### 4. Calculo das alturas relativas")

st.markdown("Para cada ponto (i) da grade, calcula-se:")

st.latex(r"\Delta h_i = C_p - (T_{n_i} - rv)")

st.markdown("""
**Convencao de sinais (DNIT 106/2009-ES e 108/2009-ES):**
- Se $\\Delta h_i > 0$ &rarr; terreno abaixo da cota &rarr; **ATERRO**
- Se $\\Delta h_i < 0$ &rarr; terreno acima da cota &rarr; **CORTE**
- Se $\\Delta h_i = 0$ &rarr; terreno coincide com a cota
""")

# ── 5. Volume bruto de corte ──
st.markdown("---")
st.markdown("### 5. Volume bruto de corte")

st.markdown("Somatorio dos deltas negativos (terreno acima da cota):")

st.latex(r"V_{corte}^{bruto} = \sum_{i \in corte} |\Delta h_i| \times A_{cel}")
st.latex(r"V_{corte}^{bruto} = {:,.2f} \; m^3".format(r.volume_corte_bruto - r.volume_talude_corte))

if r.volume_talude_corte > 0:
    st.markdown("Acrescimo do volume de talude de corte:")
    st.latex(r"V_{talude\_corte} = %.2f \; m^3" % r.volume_talude_corte)
    st.latex(
        r"V_{corte}^{bruto\;total} = %.2f + %.2f = %.2f \; m^3"
        % (r.volume_corte_bruto - r.volume_talude_corte, r.volume_talude_corte, r.volume_corte_bruto)
    )

st.markdown("Area de corte:")
st.latex(r"A_{corte} = {:,.2f} \; m^2".format(r.area_corte))

# ── 6. Volume bruto de aterro ──
st.markdown("---")
st.markdown("### 6. Volume bruto de aterro")

st.markdown("Somatorio dos deltas positivos (terreno abaixo da cota):")

st.latex(r"V_{aterro}^{bruto} = \sum_{i \in aterro} \Delta h_i \times A_{cel}")
st.latex(r"V_{aterro}^{bruto} = {:,.2f} \; m^3".format(r.volume_aterro_bruto - r.volume_talude_aterro))

if r.volume_talude_aterro > 0:
    st.markdown("Acrescimo do volume de talude de aterro:")
    st.latex(r"V_{talude\_aterro} = %.2f \; m^3" % r.volume_talude_aterro)
    st.latex(
        r"V_{aterro}^{bruto\;total} = %.2f + %.2f = %.2f \; m^3"
        % (r.volume_aterro_bruto - r.volume_talude_aterro, r.volume_talude_aterro, r.volume_aterro_bruto)
    )

st.markdown("Area de aterro:")
st.latex(r"A_{aterro} = {:,.2f} \; m^2".format(r.area_aterro))

# ── 7. Aplicacao dos fatores DNIT ──
st.markdown("---")
st.markdown("### 7. Aplicacao dos fatores DNIT")

st.markdown("**Corte empolado** (DNIT 106/2009-ES):")
st.latex(r"V_{corte}^{empolado} = V_{corte}^{bruto} \times f_e")
st.latex(
    r"V_{corte}^{empolado} = %.2f \times %.2f"
    % (r.volume_corte_bruto, fatores.empolamento)
)
st.latex(r"V_{corte}^{empolado} = {:,.2f} \; m^3".format(r.volume_corte_empolado))

st.markdown("")
st.markdown("**Aterro compactado** (DNIT 108/2009-ES):")
st.latex(r"V_{aterro}^{compactado} = V_{aterro}^{bruto} \times f_h")
st.latex(
    r"V_{aterro}^{compactado} = %.2f \times %.2f"
    % (r.volume_aterro_bruto, fatores.homogeneizacao)
)
st.latex(r"V_{aterro}^{compactado} = {:,.2f} \; m^3".format(r.volume_aterro_compactado))

# ── 8. Balanco de massa ──
st.markdown("---")
st.markdown("### 8. Balanco de massa")

st.latex(r"B = V_{corte}^{empolado} - V_{aterro}^{compactado}")
st.latex(
    r"B = %.2f - %.2f"
    % (r.volume_corte_empolado, r.volume_aterro_compactado)
)
st.latex(r"B = {:,.2f} \; m^3".format(r.balanco_massa))

if r.balanco_massa > 0:
    st.markdown("")
    st.markdown("**Resultado:** Excesso de material &rarr; **Bota-fora**")
    st.latex(r"V_{bota\text{-}fora} = B = {:,.2f} \; m^3".format(r.volume_bota_fora))
elif r.balanco_massa < 0:
    st.markdown("")
    st.markdown("**Resultado:** Deficit de material &rarr; **Solo importado**")
    st.latex(r"V_{solo\;importado} = |B| = {:,.2f} \; m^3".format(r.volume_solo_importado))
else:
    st.markdown("")
    st.markdown("**Resultado:** Balanco equilibrado &rarr; sem bota-fora nem solo importado.")

# ── 9. Quadro resumo ──
st.markdown("---")
st.markdown("### 9. Quadro resumo")

st.markdown("""
| Grandeza | Valor |
|:---------|------:|
| Area total | **{area:,.2f} m\u00b2** |
| Area de corte | **{a_corte:,.2f} m\u00b2** |
| Area de aterro | **{a_aterro:,.2f} m\u00b2** |
| Volume corte bruto | **{v_cb:,.2f} m\u00b3** |
| Volume aterro bruto | **{v_ab:,.2f} m\u00b3** |
| Volume corte empolado | **{v_ce:,.2f} m\u00b3** |
| Volume aterro compactado | **{v_ac:,.2f} m\u00b3** |
| Bota-fora | **{v_bf:,.2f} m\u00b3** |
| Solo importado | **{v_si:,.2f} m\u00b3** |
| Balanco de massa | **{bal:,.2f} m\u00b3** |
| Volume remocao vegetal | **{v_rv:,.2f} m\u00b3** |
""".format(
    area=r.area_total,
    a_corte=r.area_corte,
    a_aterro=r.area_aterro,
    v_cb=r.volume_corte_bruto,
    v_ab=r.volume_aterro_bruto,
    v_ce=r.volume_corte_empolado,
    v_ac=r.volume_aterro_compactado,
    v_bf=r.volume_bota_fora,
    v_si=r.volume_solo_importado,
    bal=r.balanco_massa,
    v_rv=r.volume_remocao_vegetal,
))

# ── Referências ──
st.markdown("---")
st.markdown("### Referencias normativas")
st.markdown("""
- DNIT 106/2009-ES — Terraplenagem: Cortes
- DNIT 108/2009-ES — Terraplenagem: Aterros
- DNIT 381/2022-PRO — Investigacao geotecnica
- DER/PR Manual de Execucao de Servicos Rodoviarios (2023)
""")
