"""Geracao de relatorio HTML com graficos e tabelas.

CSS baseado no padrao kml_saneamento (mesma paleta e componentes).
"""

from typing import List, Dict, Optional
from datetime import datetime

import plotly.graph_objects as go

from modulos.volumes import ResultadoVolume
from modulos.parametros import (
    ParametrosPadrao, NORMAS_REFERENCIA, NOMES_CATEGORIA, FATORES_DNIT,
    _resolver_categoria,
)


_CSS_BASE = """
:root {
    --azul: #1565C0;
    --azul-claro: #E3F2FD;
    --azul-escuro: #0D47A1;
    --marrom: #5D4037;
    --verde: #2E7D32;
    --cinza-bg: #F5F5F5;
    --cinza-borda: #E0E0E0;
    --cinza-texto: #424242;
    --vermelho: #C62828;
    --laranja: #EF6C00;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: var(--cinza-texto);
    background: #fff;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px 40px 20px;
    font-size: 13px;
    line-height: 1.5;
}
.header {
    background: linear-gradient(135deg, var(--azul), var(--azul-escuro));
    color: #fff;
    padding: 30px 35px;
    margin: -20px -20px 30px -20px;
    page-break-after: avoid;
}
.header h1 { font-size: 22px; margin-bottom: 6px; }
.header .subtitulo { font-size: 14px; opacity: 0.9; }
.header .meta { font-size: 11px; opacity: 0.7; margin-top: 8px; }
.header .tipo-doc {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    padding: 3px 12px;
    border-radius: 12px;
    font-size: 11px;
    margin-top: 8px;
}
.secao { margin-bottom: 24px; page-break-inside: avoid; }
.secao h2 {
    font-size: 16px;
    color: var(--azul);
    border-bottom: 2px solid var(--azul);
    padding-bottom: 6px;
    margin-bottom: 14px;
}
.secao h3 { font-size: 14px; color: var(--azul-escuro); margin: 12px 0 8px 0; }
.cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 16px;
}
.card {
    background: var(--cinza-bg);
    border-left: 3px solid var(--azul);
    padding: 12px 14px;
    border-radius: 4px;
}
.card .rotulo { font-size: 10px; text-transform: uppercase; color: #757575; }
.card .valor { font-size: 20px; font-weight: 700; margin: 4px 0; }
.card .unidade { font-size: 11px; color: #9e9e9e; }
.card.verde { border-left-color: var(--verde); }
.card.vermelho { border-left-color: var(--vermelho); }
.card.laranja { border-left-color: var(--laranja); }
.card.marrom { border-left-color: var(--marrom); }
.semaforo {
    display: flex;
    gap: 12px;
    margin: 14px 0;
}
.semaforo-item {
    flex: 1;
    padding: 14px;
    border-radius: 6px;
    text-align: center;
}
.semaforo-item.verde-bg { background: #E8F5E9; border: 1px solid #A5D6A7; }
.semaforo-item.amarelo-bg { background: #FFF8E1; border: 1px solid #FFE082; }
.semaforo-item.vermelho-bg { background: #FFEBEE; border: 1px solid #EF9A9A; }
.semaforo-item .icone { font-size: 28px; }
.semaforo-item .label { font-size: 12px; font-weight: 600; margin-top: 4px; }
.semaforo-item .detalhe { font-size: 10px; color: #757575; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
}
.badge.ok { background: #E8F5E9; color: var(--verde); }
.badge.atencao { background: #FFF3E0; color: var(--laranja); }
.badge.critico { background: #FFEBEE; color: var(--vermelho); }
.tabela-container { margin-bottom: 16px; overflow-x: auto; }
.filtro-row { display: flex; gap: 4px; margin-bottom: 6px; flex-wrap: wrap; }
.filtro-row input {
    padding: 4px 8px; border: 1px solid var(--cinza-borda);
    border-radius: 3px; font-size: 11px; flex: 1; min-width: 80px;
}
.contador-filtro { font-size: 10px; color: #9e9e9e; margin-bottom: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 11px; }
th {
    background: var(--azul); color: #fff;
    padding: 8px 10px; text-align: left;
    position: sticky; top: 0; white-space: nowrap;
}
td { padding: 6px 10px; border-bottom: 1px solid var(--cinza-borda); }
tr:nth-child(even) td { background: var(--cinza-bg); }
tr:hover td { background: var(--azul-claro); }
.footer {
    margin-top: 30px;
    padding-top: 16px;
    border-top: 1px solid var(--cinza-borda);
    font-size: 10px;
    color: #9e9e9e;
    text-align: center;
}
.progress-bar {
    height: 20px; border-radius: 10px; overflow: hidden;
    display: flex; margin: 8px 0 16px 0; background: var(--cinza-bg);
}
.progress-bar .seg-verde { background: var(--verde); }
.progress-bar .seg-amarelo { background: var(--laranja); }
.progress-bar .seg-vermelho { background: var(--vermelho); }
.grafico-container { margin: 16px 0; }
@page { size: A4; margin: 20mm 15mm; }
@media print {
    body { padding: 0; max-width: none; }
    .header { margin: -20mm -15mm 20px -15mm; padding: 20px 25px; }
    .no-print, .filtro-row, .contador-filtro { display: none; }
}
"""

_JS_FILTRO = """
<script>
function initFiltros(){
    document.querySelectorAll('.tabela-container').forEach(function(c){
        var t=c.querySelector('table');if(!t)return;
        var ths=t.querySelectorAll('th'),n=ths.length;
        var tbody=t.querySelector('tbody');
        var rows=tbody?Array.from(tbody.querySelectorAll('tr')):[];
        var total=rows.length;
        var fr=document.createElement('div');fr.className='filtro-row';
        var ct=document.createElement('div');ct.className='contador-filtro';
        ct.textContent=total+' registros';
        for(var i=0;i<n;i++){
            var inp=document.createElement('input');
            inp.placeholder=ths[i].textContent;
            inp.dataset.col=i;
            inp.addEventListener('input',function(){filtrar(c,rows,ct,total)});
            fr.appendChild(inp);
        }
        c.insertBefore(ct,t);c.insertBefore(fr,ct);
    });
}
function filtrar(c,rows,ct,total){
    var inputs=c.querySelectorAll('.filtro-row input');
    var vis=0;
    rows.forEach(function(r){
        var show=true;
        inputs.forEach(function(inp){
            var col=parseInt(inp.dataset.col);
            var val=inp.value.toLowerCase();
            if(val&&r.cells[col]){
                if(r.cells[col].textContent.toLowerCase().indexOf(val)<0)show=false;
            }
        });
        r.style.display=show?'':'none';
        if(show)vis++;
    });
    ct.textContent=vis+'/'+total+' registros';
}
document.addEventListener('DOMContentLoaded',initFiltros);
</script>
"""

# Icones para uso em f-strings (Python 3.9 nao aceita backslash em f-strings)
_ICONE_CHECK = "\u2705"
_ICONE_ALERTA = "\u26a0\ufe0f"
_ICONE_ERRO = "\u274c"
_M2 = "m\u00b2"
_M3 = "m\u00b3"


def _gerar_memoria_de_calculo(
    resultados: List[ResultadoVolume],
    parametros: ParametrosPadrao,
) -> str:
    """Gera secao HTML da memoria de calculo para cada poligono."""
    cat = _resolver_categoria(parametros.categoria_solo)
    cat_nome = NOMES_CATEGORIA[parametros.categoria_solo]
    fe = FATORES_DNIT[cat].empolamento
    fh = FATORES_DNIT[cat].homogeneizacao
    norma_cortes = NORMAS_REFERENCIA["cortes"]
    norma_aterros = NORMAS_REFERENCIA["aterros"]
    esp = parametros.espacamento_grade
    area_celula = esp ** 2
    rv = parametros.remocao_vegetal

    html = """
<div class="secao">
    <h2>Mem\u00f3ria de C\u00e1lculo</h2>"""

    for r in resultados:
        n_celulas = int(round(r.area_total / area_celula)) if area_celula > 0 else 0
        v_corte_bruto_plataforma = r.volume_corte_bruto - r.volume_talude_corte
        v_aterro_bruto_plataforma = r.volume_aterro_bruto - r.volume_talude_aterro
        razao_corte = parametros.talude_corte_h / parametros.talude_corte_v
        razao_aterro = parametros.talude_aterro_h / parametros.talude_aterro_v

        # Pre-computa strings condicionais (backslash nao permitido em f-expr)
        if r.volume_bota_fora > 0:
            linha_bota = "Balan\u00e7o > 0 \u2192 Bota-fora = {:,.2f} {}".format(
                r.volume_bota_fora, _M3)
        else:
            linha_bota = "Balan\u00e7o \u2264 0 \u2192 Bota-fora = 0,00 {}".format(_M3)
        if r.volume_solo_importado > 0:
            linha_import = "Balan\u00e7o < 0 \u2192 Solo importado = {:,.2f} {}".format(
                r.volume_solo_importado, _M3)
        else:
            linha_import = "Balan\u00e7o \u2265 0 \u2192 Solo importado = 0,00 {}".format(_M3)

        html += f"""
    <h3>{r.nome_poligono} \u2014 Cota {r.cota_projeto:.2f} m</h3>

    <p><strong>1. Dados de Entrada</strong></p>
    <table>
        <thead><tr><th>Item</th><th>Valor</th></tr></thead>
        <tbody>
            <tr><td>Cota de Projeto</td><td>{r.cota_projeto:.2f} m</td></tr>
            <tr><td>Eleva\u00e7\u00e3o M\u00e9dia do Terreno</td><td>{r.elevacao_media_terreno:.2f} m</td></tr>
            <tr><td>Espa\u00e7amento da Grade</td><td>{esp:.1f} m</td></tr>
            <tr><td>\u00c1rea da C\u00e9lula (espa\u00e7amento\u00b2)</td><td>{area_celula:,.1f} {_M2}</td></tr>
            <tr><td>N\u00ba de C\u00e9lulas V\u00e1lidas</td><td>{n_celulas:,}</td></tr>
            <tr><td>Remo\u00e7\u00e3o Vegetal</td><td>{rv:.2f} m</td></tr>
            <tr><td>Categoria do Solo</td><td>{cat_nome}</td></tr>
        </tbody>
    </table>

    <p><strong>2. Remo\u00e7\u00e3o Vegetal</strong></p>
    <table>
        <thead><tr><th>F\u00f3rmula</th><th>C\u00e1lculo</th><th>Resultado</th></tr></thead>
        <tbody>
            <tr>
                <td>V<sub>remo\u00e7\u00e3o</sub> = N<sub>c\u00e9lulas</sub> \u00d7 A<sub>c\u00e9lula</sub> \u00d7 espessura</td>
                <td>{n_celulas:,} \u00d7 {area_celula:,.1f} \u00d7 {rv:.2f}</td>
                <td>{r.volume_remocao_vegetal:,.2f} {_M3}</td>
            </tr>
        </tbody>
    </table>

    <p><strong>3. C\u00e1lculo de Volumes \u2014 M\u00e9todo de Grade</strong></p>
    <div style="background:var(--cinza-bg);padding:10px 14px;border-radius:4px;font-family:monospace;font-size:11px;margin:8px 0;">
        terreno_ajustado = eleva\u00e7\u00e3o \u2212 remo\u00e7\u00e3o_vegetal<br>
        \u0394 = cota_projeto \u2212 terreno_ajustado<br><br>
        Se \u0394 &lt; 0 \u2192 <strong>CORTE</strong> &nbsp;(terreno acima do projeto)<br>
        Se \u0394 &gt; 0 \u2192 <strong>ATERRO</strong> (terreno abaixo do projeto)<br><br>
        V<sub>corte_bruto</sub>&nbsp; = \u03a3 |\u0394\u1d62| \u00d7 A<sub>c\u00e9lula</sub> &nbsp;(para \u0394\u1d62 &lt; 0)<br>
        V<sub>aterro_bruto</sub> = \u03a3 &nbsp;\u0394\u1d62 &nbsp;\u00d7 A<sub>c\u00e9lula</sub> &nbsp;(para \u0394\u1d62 &gt; 0)
    </div>
    <table>
        <thead><tr><th>Grandeza</th><th>Valor</th></tr></thead>
        <tbody>
            <tr><td>Corte bruto plataforma (in-situ)</td><td>{v_corte_bruto_plataforma:,.2f} {_M3}</td></tr>
            <tr><td>Aterro bruto plataforma (in-situ)</td><td>{v_aterro_bruto_plataforma:,.2f} {_M3}</td></tr>
            <tr><td>\u00c1rea de corte</td><td>{r.area_corte:,.0f} {_M2}</td></tr>
            <tr><td>\u00c1rea de aterro</td><td>{r.area_aterro:,.0f} {_M2}</td></tr>
        </tbody>
    </table>

    <p><strong>4. Volumes de Talude (bordas do pol\u00edgono)</strong></p>
    <div style="background:var(--cinza-bg);padding:10px 14px;border-radius:4px;font-family:monospace;font-size:11px;margin:8px 0;">
        V<sub>talude</sub> = \u03a3 (0,5 \u00d7 h\u1d62\u00b2 \u00d7 (H/V) \u00d7 espa\u00e7amento)<br><br>
        Talude de corte: &nbsp;H:V = {parametros.talude_corte_h:.0f}:{parametros.talude_corte_v:.0f} \u2192 raz\u00e3o = {razao_corte:.1f}<br>
        Talude de aterro: H:V = {parametros.talude_aterro_h:.0f}:{parametros.talude_aterro_v:.0f} \u2192 raz\u00e3o = {razao_aterro:.1f}
    </div>
    <table>
        <thead><tr><th>Talude</th><th>Volume</th></tr></thead>
        <tbody>
            <tr><td>Corte (borda)</td><td>{r.volume_talude_corte:,.2f} {_M3}</td></tr>
            <tr><td>Aterro (borda)</td><td>{r.volume_talude_aterro:,.2f} {_M3}</td></tr>
        </tbody>
    </table>
    <p style="font-size:10px;color:#757575;margin-top:4px;">
        <em>Volumes de talude somados aos volumes brutos antes da aplica\u00e7\u00e3o dos fatores DNIT.</em>
    </p>

    <p><strong>5. Aplica\u00e7\u00e3o dos Fatores DNIT</strong></p>
    <div style="background:var(--cinza-bg);padding:10px 14px;border-radius:4px;font-family:monospace;font-size:11px;margin:8px 0;">
        Fator de Empolamento ({norma_cortes}): &nbsp;&nbsp;f<sub>e</sub> = {fe}<br>
        Fator de Homogeneiza\u00e7\u00e3o ({norma_aterros}): f<sub>h</sub> = {fh}<br><br>
        V<sub>corte_empolado</sub> &nbsp;&nbsp;&nbsp;= V<sub>corte_bruto</sub> \u00d7 f<sub>e</sub> = {r.volume_corte_bruto:,.2f} \u00d7 {fe} = <strong>{r.volume_corte_empolado:,.2f} {_M3}</strong><br>
        V<sub>aterro_compactado</sub> = V<sub>aterro_bruto</sub> \u00d7 f<sub>h</sub> = {r.volume_aterro_bruto:,.2f} \u00d7 {fh} = <strong>{r.volume_aterro_compactado:,.2f} {_M3}</strong>
    </div>

    <p><strong>6. Balan\u00e7o de Massa</strong></p>
    <div style="background:var(--cinza-bg);padding:10px 14px;border-radius:4px;font-family:monospace;font-size:11px;margin:8px 0;">
        Balan\u00e7o = V<sub>corte_empolado</sub> \u2212 V<sub>aterro_compactado</sub><br>
        Balan\u00e7o = {r.volume_corte_empolado:,.2f} \u2212 {r.volume_aterro_compactado:,.2f} = <strong>{r.balanco_massa:,.2f} {_M3}</strong><br><br>
        {linha_bota}<br>
        {linha_import}
    </div>

    <p><strong>7. Resumo Final</strong></p>
    <table>
        <thead><tr><th>Grandeza</th><th>Valor</th><th>Unidade</th></tr></thead>
        <tbody>
            <tr><td>Corte bruto (in-situ)</td><td>{r.volume_corte_bruto:,.2f}</td><td>{_M3}</td></tr>
            <tr><td>Aterro bruto (in-situ)</td><td>{r.volume_aterro_bruto:,.2f}</td><td>{_M3}</td></tr>
            <tr><td>Corte empolado</td><td>{r.volume_corte_empolado:,.2f}</td><td>{_M3}</td></tr>
            <tr><td>Aterro compactado</td><td>{r.volume_aterro_compactado:,.2f}</td><td>{_M3}</td></tr>
            <tr><td>Bota-fora</td><td>{r.volume_bota_fora:,.2f}</td><td>{_M3}</td></tr>
            <tr><td>Solo importado</td><td>{r.volume_solo_importado:,.2f}</td><td>{_M3}</td></tr>
            <tr><td>Remo\u00e7\u00e3o vegetal</td><td>{r.volume_remocao_vegetal:,.2f}</td><td>{_M3}</td></tr>
        </tbody>
    </table>
    <hr style="margin:20px 0;border:none;border-top:1px dashed var(--cinza-borda);">"""

    html += "\n</div>"
    return html


def gerar_relatorio_gerencial(
    resultados: List[ResultadoVolume],
    parametros: ParametrosPadrao,
    titulo: str = "Relat\u00f3rio Gerencial de Terraplenagem",
) -> str:
    """Gera relatorio HTML gerencial (resumo executivo com KPIs)."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    total_corte = sum(r.volume_corte_empolado for r in resultados)
    total_aterro = sum(r.volume_aterro_compactado for r in resultados)
    total_bota = sum(r.volume_bota_fora for r in resultados)
    total_import = sum(r.volume_solo_importado for r in resultados)
    total_area = sum(r.area_total for r in resultados)
    balanco_total = total_corte - total_aterro
    num_poly = len(resultados)

    # Semaforo principal
    if abs(balanco_total) < max(total_corte * 0.05, 1.0):
        semaforo_cls = "verde-bg"
        semaforo_icone = _ICONE_CHECK
        semaforo_label = "Balanceado"
        semaforo_detalhe = "Corte e aterro equilibrados"
    elif total_bota > total_import:
        semaforo_cls = "amarelo-bg"
        semaforo_icone = _ICONE_ALERTA
        semaforo_label = "Excesso de Corte"
        semaforo_detalhe = "Bota-fora: {:,.1f} {}".format(total_bota, _M3)
    else:
        semaforo_cls = "vermelho-bg"
        semaforo_icone = _ICONE_ERRO
        semaforo_label = "D\u00e9ficit de Material"
        semaforo_detalhe = "Solo importado: {:,.1f} {}".format(total_import, _M3)

    # Semaforo secundarios
    bota_cls = "amarelo-bg" if total_bota > 0 else "verde-bg"
    bota_icone = _ICONE_ALERTA if total_bota > 0 else _ICONE_CHECK
    import_cls = "vermelho-bg" if total_import > 0 else "verde-bg"
    import_icone = _ICONE_ERRO if total_import > 0 else _ICONE_CHECK

    cat_nome = NOMES_CATEGORIA[parametros.categoria_solo]
    fator_emp = FATORES_DNIT[_resolver_categoria(parametros.categoria_solo)].empolamento
    fator_hom = FATORES_DNIT[_resolver_categoria(parametros.categoria_solo)].homogeneizacao
    norma_cortes = NORMAS_REFERENCIA["cortes"]
    norma_aterros = NORMAS_REFERENCIA["aterros"]
    normas_todas = ", ".join(NORMAS_REFERENCIA.values())

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{titulo}</title>
<style>{_CSS_BASE}</style>
</head>
<body>
<div class="header">
    <h1>{titulo}</h1>
    <div class="subtitulo">Resumo Executivo - {num_poly} pol\u00edgono(s) analisado(s)</div>
    <div class="meta">Gerado em {agora}</div>
    <div class="tipo-doc">Memorial Gerencial</div>
</div>

<div class="secao">
    <h2>Indicadores Gerais</h2>
    <div class="cards">
        <div class="card">
            <div class="rotulo">\u00c1rea Total</div>
            <div class="valor">{total_area:,.0f}</div>
            <div class="unidade">{_M2}</div>
        </div>
        <div class="card vermelho">
            <div class="rotulo">Corte Empolado</div>
            <div class="valor">{total_corte:,.1f}</div>
            <div class="unidade">{_M3}</div>
        </div>
        <div class="card">
            <div class="rotulo">Aterro Compactado</div>
            <div class="valor">{total_aterro:,.1f}</div>
            <div class="unidade">{_M3}</div>
        </div>
        <div class="card laranja">
            <div class="rotulo">Balan\u00e7o</div>
            <div class="valor">{balanco_total:,.1f}</div>
            <div class="unidade">{_M3}</div>
        </div>
    </div>

    <div class="semaforo">
        <div class="semaforo-item {semaforo_cls}">
            <div class="icone">{semaforo_icone}</div>
            <div class="label">{semaforo_label}</div>
            <div class="detalhe">{semaforo_detalhe}</div>
        </div>
        <div class="semaforo-item {bota_cls}">
            <div class="icone">{bota_icone}</div>
            <div class="label">Bota-fora</div>
            <div class="detalhe">{total_bota:,.1f} {_M3}</div>
        </div>
        <div class="semaforo-item {import_cls}">
            <div class="icone">{import_icone}</div>
            <div class="label">Solo Importado</div>
            <div class="detalhe">{total_import:,.1f} {_M3}</div>
        </div>
    </div>
</div>

<div class="secao">
    <h2>Par\u00e2metros Utilizados</h2>
    <table>
        <thead><tr>
            <th>Par\u00e2metro</th><th>Valor</th><th>Refer\u00eancia</th>
        </tr></thead>
        <tbody>
            <tr><td>Categoria do Solo</td><td>{cat_nome}</td><td>DNIT</td></tr>
            <tr><td>Fator Empolamento</td><td>{fator_emp}</td><td>{norma_cortes}</td></tr>
            <tr><td>Fator Homogeneiza\u00e7\u00e3o</td><td>{fator_hom}</td><td>{norma_aterros}</td></tr>
            <tr><td>Remo\u00e7\u00e3o Vegetal</td><td>{parametros.remocao_vegetal:.2f} m</td><td>Premissa</td></tr>
            <tr><td>Talude de Corte</td><td>{parametros.talude_corte_h:.0f}:{parametros.talude_corte_v:.0f}</td><td>Premissa</td></tr>
            <tr><td>Talude de Aterro</td><td>{parametros.talude_aterro_h:.0f}:{parametros.talude_aterro_v:.0f}</td><td>Premissa</td></tr>
            <tr><td>Espa\u00e7amento da Grade</td><td>{parametros.espacamento_grade:.1f} m</td><td>Premissa</td></tr>
        </tbody>
    </table>
</div>

<div class="secao">
    <h2>Resumo por Pol\u00edgono</h2>
    <div class="tabela-container">
    <table>
        <thead><tr>
            <th>Pol\u00edgono</th><th>Cota (m)</th><th>\u00c1rea ({_M2})</th>
            <th>Corte ({_M3})</th><th>Aterro ({_M3})</th>
            <th>Bota-fora ({_M3})</th><th>Solo Import. ({_M3})</th><th>Status</th>
        </tr></thead>
        <tbody>"""

    for r in resultados:
        corte_ref = r.volume_corte_empolado if r.volume_corte_empolado > 0 else 1.0
        if abs(r.balanco_massa) < corte_ref * 0.05:
            badge_cls, badge_txt = "ok", "Equilibrado"
        elif r.volume_bota_fora > 0:
            badge_cls, badge_txt = "atencao", "Exc. Corte"
        else:
            badge_cls, badge_txt = "critico", "D\u00e9ficit"

        html += f"""
            <tr>
                <td>{r.nome_poligono}</td>
                <td>{r.cota_projeto:.2f}</td>
                <td>{r.area_total:,.0f}</td>
                <td>{r.volume_corte_empolado:,.1f}</td>
                <td>{r.volume_aterro_compactado:,.1f}</td>
                <td>{r.volume_bota_fora:,.1f}</td>
                <td>{r.volume_solo_importado:,.1f}</td>
                <td><span class="badge {badge_cls}">{badge_txt}</span></td>
            </tr>"""

    html += f"""
        </tbody>
    </table>
    </div>
</div>

<div class="footer">
    Relat\u00f3rio gerado automaticamente | Normas: {normas_todas} | {agora}
</div>
{_JS_FILTRO}
</body>
</html>"""

    return html


def gerar_relatorio_analitico(
    resultados: List[ResultadoVolume],
    figuras: Dict[str, go.Figure],
    parametros: ParametrosPadrao,
    titulo: str = "Relat\u00f3rio Anal\u00edtico de Terraplenagem",
) -> str:
    """Gera relatorio HTML analitico completo com graficos Plotly."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    num_poly = len(resultados)

    cat_nome = NOMES_CATEGORIA[parametros.categoria_solo]
    fator_emp = FATORES_DNIT[_resolver_categoria(parametros.categoria_solo)].empolamento
    fator_hom = FATORES_DNIT[_resolver_categoria(parametros.categoria_solo)].homogeneizacao
    norma_cortes = NORMAS_REFERENCIA["cortes"]
    norma_aterros = NORMAS_REFERENCIA["aterros"]
    normas_todas = ", ".join(NORMAS_REFERENCIA.values())

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{titulo}</title>
<style>{_CSS_BASE}</style>
</head>
<body>
<div class="header">
    <h1>{titulo}</h1>
    <div class="subtitulo">Relat\u00f3rio T\u00e9cnico Completo - {num_poly} pol\u00edgono(s)</div>
    <div class="meta">Gerado em {agora}</div>
    <div class="tipo-doc">Memorial Anal\u00edtico</div>
</div>

<div class="secao">
    <h2>Par\u00e2metros T\u00e9cnicos</h2>
    <table>
        <thead><tr><th>Par\u00e2metro</th><th>Valor</th><th>Norma</th></tr></thead>
        <tbody>
            <tr><td>Categoria</td><td>{cat_nome}</td><td>DNIT</td></tr>
            <tr><td>Empolamento</td><td>{fator_emp}</td><td>{norma_cortes}</td></tr>
            <tr><td>Homogeneiza\u00e7\u00e3o</td><td>{fator_hom}</td><td>{norma_aterros}</td></tr>
            <tr><td>Remo\u00e7\u00e3o Vegetal</td><td>{parametros.remocao_vegetal:.2f} m</td><td>-</td></tr>
            <tr><td>Talude Corte</td><td>{parametros.talude_corte_h:.0f}:{parametros.talude_corte_v:.0f}</td><td>-</td></tr>
            <tr><td>Talude Aterro</td><td>{parametros.talude_aterro_h:.0f}:{parametros.talude_aterro_v:.0f}</td><td>-</td></tr>
        </tbody>
    </table>
</div>"""

    # Graficos (excluindo os removidos do analitico)
    _graficos_excluidos = {"3D Compara\u00e7\u00e3o", "Diagrama de Br\u00fcckner", "Volumes por Pol\u00edgono"}
    primeiro_grafico = True
    for nome, fig in figuras.items():
        if any(nome.startswith(excl) for excl in _graficos_excluidos):
            continue
        fig_html = fig.to_html(
            full_html=False,
            include_plotlyjs='cdn' if primeiro_grafico else False,
        )
        primeiro_grafico = False
        html += f"""
<div class="secao">
    <h2>{nome}</h2>
    <div class="grafico-container">{fig_html}</div>
</div>"""

    # Memoria de calculo
    html += _gerar_memoria_de_calculo(resultados, parametros)

    # Tabela detalhada
    html += """
<div class="secao">
    <h2>Detalhamento por Pol\u00edgono</h2>
    <div class="tabela-container">
    <table>
        <thead><tr>
            <th>Pol\u00edgono</th><th>Cota (m)</th><th>Elev. M\u00e9dia (m)</th>
            <th>\u00c1rea (m\u00b2)</th><th>\u00c1rea Corte (m\u00b2)</th><th>\u00c1rea Aterro (m\u00b2)</th>
            <th>Corte Bruto (m\u00b3)</th><th>Aterro Bruto (m\u00b3)</th>
            <th>Corte Empolado (m\u00b3)</th><th>Aterro Compact. (m\u00b3)</th>
            <th>Bota-fora (m\u00b3)</th><th>Solo Import. (m\u00b3)</th>
            <th>Balan\u00e7o (m\u00b3)</th>
            <th>Rem. Vegetal (m\u00b3)</th>
            <th>Talude Corte (m\u00b3)</th><th>Talude Aterro (m\u00b3)</th>
        </tr></thead>
        <tbody>"""

    for r in resultados:
        html += f"""
            <tr>
                <td>{r.nome_poligono}</td>
                <td>{r.cota_projeto:.2f}</td>
                <td>{r.elevacao_media_terreno:.2f}</td>
                <td>{r.area_total:,.0f}</td>
                <td>{r.area_corte:,.0f}</td>
                <td>{r.area_aterro:,.0f}</td>
                <td>{r.volume_corte_bruto:,.2f}</td>
                <td>{r.volume_aterro_bruto:,.2f}</td>
                <td>{r.volume_corte_empolado:,.2f}</td>
                <td>{r.volume_aterro_compactado:,.2f}</td>
                <td>{r.volume_bota_fora:,.2f}</td>
                <td>{r.volume_solo_importado:,.2f}</td>
                <td>{r.balanco_massa:,.2f}</td>
                <td>{r.volume_remocao_vegetal:,.2f}</td>
                <td>{r.volume_talude_corte:,.2f}</td>
                <td>{r.volume_talude_aterro:,.2f}</td>
            </tr>"""

    # Totais
    t_area = sum(r.area_total for r in resultados)
    t_ac = sum(r.area_corte for r in resultados)
    t_aa = sum(r.area_aterro for r in resultados)
    t_cb = sum(r.volume_corte_bruto for r in resultados)
    t_ab = sum(r.volume_aterro_bruto for r in resultados)
    t_ce = sum(r.volume_corte_empolado for r in resultados)
    t_acomp = sum(r.volume_aterro_compactado for r in resultados)
    t_bf = sum(r.volume_bota_fora for r in resultados)
    t_si = sum(r.volume_solo_importado for r in resultados)
    t_bal = sum(r.balanco_massa for r in resultados)
    t_rv = sum(r.volume_remocao_vegetal for r in resultados)
    t_tc = sum(r.volume_talude_corte for r in resultados)
    t_ta = sum(r.volume_talude_aterro for r in resultados)

    html += f"""
            <tr style="font-weight:700;background:#E3F2FD">
                <td>TOTAL</td>
                <td>-</td><td>-</td>
                <td>{t_area:,.0f}</td>
                <td>{t_ac:,.0f}</td>
                <td>{t_aa:,.0f}</td>
                <td>{t_cb:,.2f}</td>
                <td>{t_ab:,.2f}</td>
                <td>{t_ce:,.2f}</td>
                <td>{t_acomp:,.2f}</td>
                <td>{t_bf:,.2f}</td>
                <td>{t_si:,.2f}</td>
                <td>{t_bal:,.2f}</td>
                <td>{t_rv:,.2f}</td>
                <td>{t_tc:,.2f}</td>
                <td>{t_ta:,.2f}</td>
            </tr>
        </tbody>
    </table>
    </div>
</div>

<div class="footer">
    Relat\u00f3rio gerado automaticamente | Normas: {normas_todas} | {agora}
</div>
{_JS_FILTRO}
</body>
</html>"""

    return html


def gerar_relatorio_html(
    resultados: List[ResultadoVolume],
    figuras: Dict[str, go.Figure],
    parametros: ParametrosPadrao,
) -> Dict[str, str]:
    """Gera ambos os relatorios (gerencial e analitico).

    Returns:
        Dict com chaves 'gerencial' e 'analitico', valores HTML string.
    """
    return {
        "gerencial": gerar_relatorio_gerencial(resultados, parametros),
        "analitico": gerar_relatorio_analitico(resultados, figuras, parametros),
    }
