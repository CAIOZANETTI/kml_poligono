"""Visualizacoes Plotly para terraplenagem — tema minimalista."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional

from modulos.terreno import SuperficieTerreno, gerar_superficie_projeto
from modulos.volumes import ResultadoVolume
from modulos.bruckner import ResultadoBruckner
from modulos.geometria import GradePoligono
from modulos.tema import CORES, PLOTLY_LAYOUT, PLOTLY_SCENE


def _aplicar_layout(fig: go.Figure, titulo: str, height: int = 560, **kwargs):
    """Aplica layout minimalista padrao a uma figura Plotly."""
    layout = {**PLOTLY_LAYOUT, "height": height}
    layout["title"] = dict(text=titulo, font=dict(size=14, color="#27272a"), x=0, xanchor="left")
    layout.update(kwargs)
    fig.update_layout(**layout)


def criar_mapa_contorno(
    superficie: SuperficieTerreno,
    titulo: str = "curvas de nivel",
) -> go.Figure:
    """Cria mapa de curvas de nivel do terreno natural."""
    fig = go.Figure(data=go.Contour(
        x=superficie.grade_x,
        y=superficie.grade_y,
        z=superficie.elevacao_malha,
        colorscale="Earth",
        contours=dict(
            showlabels=True,
            labelfont=dict(size=9, color="white"),
        ),
        colorbar=dict(title="elev. (m)", titlefont=dict(size=10), tickfont=dict(size=9)),
    ))

    _aplicar_layout(fig, titulo, height=560,
                    yaxis_scaleanchor="x")
    return fig


# ── Helpers 3D: exagero vertical e elevacao relativa ──

def _preparar_z_3d(
    elevacao_malha: np.ndarray,
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> tuple:
    """Prepara dados Z para visualizacao 3D.

    Args:
        elevacao_malha: 2D array de elevacoes.
        exagero_vertical: Multiplicador do eixo Z (1-5).
        cota_referencia: Se fornecido, converte para alturas relativas (corte/aterro).

    Returns:
        (z_data, z_label, colorscale, colorbar_dict)
    """
    if cota_referencia is not None:
        z_data = elevacao_malha - cota_referencia
        z_label = "altura (m) [- corte / + aterro]"
        colorscale = "RdBu"
        vmax = float(np.nanmax(np.abs(z_data)))
        colorbar = dict(
            title="altura (m)", titlefont=dict(size=10), tickfont=dict(size=9),
        )
        if exagero_vertical > 1:
            z_data = z_data * exagero_vertical
            z_label += " ({}x)".format(exagero_vertical)
        return z_data, z_label, colorscale, colorbar
    else:
        z_data = elevacao_malha
        z_label = "elev. (m)"
        if exagero_vertical > 1:
            z_media = float(np.nanmean(z_data))
            z_data = (z_data - z_media) * exagero_vertical + z_media
            z_label += " (exagero {}x)".format(exagero_vertical)
        return z_data, z_label, None, dict(
            title="elev. (m)", titlefont=dict(size=10), tickfont=dict(size=9),
        )


def _preparar_z_borda(
    borda_z: np.ndarray,
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
    z_media: Optional[float] = None,
) -> np.ndarray:
    """Aplica mesma transformacao Z nos pontos de borda."""
    if cota_referencia is not None:
        borda_z_out = borda_z - cota_referencia
        if exagero_vertical > 1:
            borda_z_out = borda_z_out * exagero_vertical
        return borda_z_out
    elif exagero_vertical > 1 and z_media is not None:
        return (borda_z - z_media) * exagero_vertical + z_media
    return borda_z


def criar_superficie_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "terreno 3d",
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> go.Figure:
    """Cria visualizacao 3D do terreno natural usando go.Surface."""
    fig = go.Figure()

    z_data, z_label, colorscale, colorbar = _preparar_z_3d(
        superficie.elevacao_malha, exagero_vertical, cota_referencia,
    )

    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=z_data,
        colorscale=colorscale or "Earth",
        colorbar=colorbar,
        name="terreno natural",
        connectgaps=True,
    ))

    if grade is not None:
        borda = grade.pontos_borda
        borda_fechada = np.vstack([borda, borda[0:1]])
        z_media = float(np.nanmean(superficie.elevacao_malha))
        borda_z = _preparar_z_borda(
            borda_fechada[:, 2], exagero_vertical, cota_referencia, z_media,
        )
        fig.add_trace(go.Scatter3d(
            x=borda_fechada[:, 0],
            y=borda_fechada[:, 1],
            z=borda_z,
            mode="lines+markers",
            line=dict(color=CORES["corte"], width=3),
            marker=dict(size=2, color=CORES["corte"]),
            name="borda",
        ))

    scene = {**PLOTLY_SCENE, "aspectmode": "data",
             "xaxis": {**PLOTLY_SCENE["xaxis"], "title": "easting (m)"},
             "yaxis": {**PLOTLY_SCENE["yaxis"], "title": "northing (m)"},
             "zaxis": {**PLOTLY_SCENE["zaxis"], "title": z_label}}

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=titulo, font=dict(size=14, color="#27272a"), x=0, xanchor="left"),
        scene=scene,
        height=640,
    )
    return fig


def criar_superficie_3d_contornos(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "terreno 3d (contornos)",
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> go.Figure:
    """Cria Surface 3D com contornos projetados no plano Z."""
    fig = go.Figure()

    z_data, z_label, colorscale, colorbar = _preparar_z_3d(
        superficie.elevacao_malha, exagero_vertical, cota_referencia,
    )

    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=z_data,
        colorscale=colorscale or "Viridis",
        colorbar=colorbar if colorscale else dict(
            title="elev. (m)", titlefont=dict(size=10), tickfont=dict(size=9),
        ),
        name="terreno natural",
        connectgaps=True,
        contours_z=dict(
            show=True,
            usecolormap=True,
            highlightcolor="#a3e635",
            project_z=True,
        ),
    ))

    if grade is not None:
        borda = grade.pontos_borda
        borda_fechada = np.vstack([borda, borda[0:1]])
        z_media = float(np.nanmean(superficie.elevacao_malha))
        borda_z = _preparar_z_borda(
            borda_fechada[:, 2], exagero_vertical, cota_referencia, z_media,
        )
        fig.add_trace(go.Scatter3d(
            x=borda_fechada[:, 0],
            y=borda_fechada[:, 1],
            z=borda_z,
            mode="lines+markers",
            line=dict(color=CORES["corte"], width=3),
            marker=dict(size=2, color=CORES["corte"]),
            name="borda",
        ))

    scene = {**PLOTLY_SCENE, "aspectmode": "data",
             "camera": dict(eye=dict(x=1.87, y=0.88, z=-0.64)),
             "xaxis": {**PLOTLY_SCENE["xaxis"], "title": "easting (m)"},
             "yaxis": {**PLOTLY_SCENE["yaxis"], "title": "northing (m)"},
             "zaxis": {**PLOTLY_SCENE["zaxis"], "title": z_label}}

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=titulo, font=dict(size=14, color="#27272a"), x=0, xanchor="left"),
        scene=scene,
        height=640,
    )
    return fig


def criar_comparacao_3d(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    remocao_vegetal: float = 0.30,
    titulo: str = "terreno vs projeto",
) -> go.Figure:
    """Cria visualizacao 3D comparando terreno com superficie de projeto."""
    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=superficie.elevacao_malha,
        colorscale="Earth",
        opacity=0.85,
        name="terreno natural",
        showscale=False,
        connectgaps=True,
    ))

    superficie_proj = gerar_superficie_projeto(superficie, cota_projeto)
    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=superficie_proj,
        colorscale=[[0, "rgba(99,102,241,0.45)"], [1, "rgba(99,102,241,0.45)"]],
        opacity=0.5,
        showscale=False,
        name="projeto ({:.2f}m)".format(cota_projeto),
        connectgaps=True,
    ))

    scene = {**PLOTLY_SCENE, "aspectmode": "data",
             "xaxis": {**PLOTLY_SCENE["xaxis"], "title": "easting (m)"},
             "yaxis": {**PLOTLY_SCENE["yaxis"], "title": "northing (m)"},
             "zaxis": {**PLOTLY_SCENE["zaxis"], "title": "elev. (m)"}}

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=titulo, font=dict(size=14, color="#27272a"), x=0, xanchor="left"),
        scene=scene,
        height=640,
    )
    return fig


def criar_mapa_corte_aterro(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    remocao_vegetal: float = 0.30,
    titulo: str = "corte / aterro",
) -> go.Figure:
    """Cria mapa 2D com zonas de corte (vermelho) e aterro (azul)."""
    terreno_ajustado = superficie.elevacao_malha - remocao_vegetal
    delta = cota_projeto - terreno_ajustado

    vmax = max(abs(np.nanmin(delta)), abs(np.nanmax(delta)))

    fig = go.Figure(data=go.Heatmap(
        x=superficie.grade_x,
        y=superficie.grade_y,
        z=delta,
        colorscale="RdBu",
        zmid=0,
        zmin=-vmax,
        zmax=vmax,
        colorbar=dict(
            title="delta (m)",
            titlefont=dict(size=10),
            tickfont=dict(size=9),
        ),
    ))

    _aplicar_layout(fig, titulo, height=560,
                    yaxis_scaleanchor="x")
    return fig


def criar_perfil_transversal(
    superficie: SuperficieTerreno,
    grade: GradePoligono,
    cota_projeto: float,
    posicao_y: Optional[float] = None,
    remocao_vegetal: float = 0.30,
    talude_corte: tuple = (1, 1),
    talude_aterro: tuple = (1, 2),
    titulo: str = "perfil transversal",
) -> go.Figure:
    """Cria perfil transversal (corte) em uma posicao Y fixa."""
    pontos = superficie.pontos_grade_xy
    elevacoes = superficie.elevacao_grade

    if posicao_y is None:
        posicao_y = np.median(pontos[:, 1])

    tolerancia = grade.espacamento * 0.6
    mascara = np.abs(pontos[:, 1] - posicao_y) < tolerancia
    if mascara.sum() < 2:
        tolerancia = grade.espacamento * 1.5
        mascara = np.abs(pontos[:, 1] - posicao_y) < tolerancia

    xs = pontos[mascara, 0]
    zs = elevacoes[mascara]

    ordem = np.argsort(xs)
    xs = xs[ordem]
    zs = zs[ordem]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=xs, y=zs,
        mode="lines",
        name="terreno natural",
        line=dict(color="#78716c", width=2),
        fill="tozeroy",
        fillcolor="rgba(120,113,108,0.06)",
    ))

    zs_ajustado = zs - remocao_vegetal
    fig.add_trace(go.Scatter(
        x=xs, y=zs_ajustado,
        mode="lines",
        name="terreno (-{:.1f}m)".format(remocao_vegetal),
        line=dict(color="#a8a29e", width=1, dash="dash"),
    ))

    fig.add_trace(go.Scatter(
        x=[xs[0], xs[-1]],
        y=[cota_projeto, cota_projeto],
        mode="lines",
        name="projeto ({:.2f}m)".format(cota_projeto),
        line=dict(color=CORES["accent"], width=2),
    ))

    delta = cota_projeto - zs_ajustado
    corte_y = np.where(delta < 0, zs_ajustado, cota_projeto)
    aterro_y = np.where(delta > 0, zs_ajustado, cota_projeto)

    fig.add_trace(go.Scatter(
        x=xs, y=corte_y,
        fill="tonexty",
        fillcolor="rgba(225,29,72,0.15)",
        line=dict(width=0),
        name="corte",
    ))

    fig.add_trace(go.Scatter(
        x=xs, y=aterro_y,
        fill="tonexty",
        fillcolor="rgba(99,102,241,0.15)",
        line=dict(width=0),
        name="aterro",
    ))

    _aplicar_layout(fig, "{} (Y = {:.1f}m)".format(titulo, posicao_y), height=440,
                    legend=dict(x=0.01, y=0.99))
    return fig


def criar_diagrama_bruckner(
    resultado: ResultadoBruckner,
    titulo: str = "diagrama de bruckner",
) -> go.Figure:
    """Cria diagrama de Bruckner (curva de massa)."""
    fig = go.Figure()

    pos = resultado.posicoes
    vol = resultado.volumes_acumulados

    fig.add_trace(go.Scatter(
        x=pos, y=vol,
        mode="lines",
        name="volume acumulado",
        line=dict(color=CORES["accent"], width=2),
    ))

    vol_pos = np.where(vol > 0, vol, 0)
    vol_neg = np.where(vol < 0, vol, 0)

    fig.add_trace(go.Scatter(
        x=pos, y=vol_pos,
        fill="tozeroy",
        fillcolor="rgba(225,29,72,0.1)",
        line=dict(width=0),
        name="bota-fora",
    ))

    fig.add_trace(go.Scatter(
        x=pos, y=vol_neg,
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.1)",
        line=dict(width=0),
        name="emprestimo",
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="#d4d4d8", line_width=1)

    for eq in resultado.pontos_equilibrio:
        fig.add_vline(
            x=eq, line_dash="dot", line_color=CORES["success"], line_width=1,
            annotation_text="{:.1f}m".format(eq),
            annotation_font=dict(size=9, color=CORES["success"]),
        )

    _aplicar_layout(fig, titulo, height=440)
    return fig


def criar_tabela_volumes(
    resultados: List[ResultadoVolume],
    titulo: str = "resumo de volumes",
) -> go.Figure:
    """Cria tabela formatada com volumes de corte e aterro."""
    headers = [
        "poligono", "area (m\u00b2)", "corte bruto (m\u00b3)",
        "aterro bruto (m\u00b3)", "corte empolado (m\u00b3)",
        "aterro compact. (m\u00b3)", "bota-fora (m\u00b3)",
        "solo import. (m\u00b3)", "balanco (m\u00b3)",
    ]

    valores = [[] for _ in headers]
    for r in resultados:
        valores[0].append(r.nome_poligono)
        valores[1].append("{:,.1f}".format(r.area_total))
        valores[2].append("{:,.2f}".format(r.volume_corte_bruto))
        valores[3].append("{:,.2f}".format(r.volume_aterro_bruto))
        valores[4].append("{:,.2f}".format(r.volume_corte_empolado))
        valores[5].append("{:,.2f}".format(r.volume_aterro_compactado))
        valores[6].append("{:,.2f}".format(r.volume_bota_fora))
        valores[7].append("{:,.2f}".format(r.volume_solo_importado))
        valores[8].append("{:,.2f}".format(r.balanco_massa))

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color="#27272a",
            font=dict(color="#fafafa", size=10, family="Inter, sans-serif"),
            align="center",
            height=32,
        ),
        cells=dict(
            values=valores,
            fill_color=[["#fafafa", "#ffffff"] * ((len(resultados) + 1) // 2)] * len(headers),
            align="center",
            font=dict(size=10, color="#3f3f46", family="Inter, sans-serif"),
            height=28,
        ),
    )])

    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color="#27272a"), x=0, xanchor="left"),
        height=max(260, 80 + 36 * len(resultados)),
        margin=dict(l=0, r=0, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def criar_grafico_barras_volumes(
    resultados: List[ResultadoVolume],
    titulo: str = "volumes por poligono",
) -> go.Figure:
    """Cria grafico de barras agrupadas com volumes por poligono."""
    nomes = [r.nome_poligono for r in resultados]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="corte empolado",
        x=nomes,
        y=[r.volume_corte_empolado for r in resultados],
        marker_color=CORES["corte"],
    ))
    fig.add_trace(go.Bar(
        name="aterro compactado",
        x=nomes,
        y=[r.volume_aterro_compactado for r in resultados],
        marker_color=CORES["aterro"],
    ))
    fig.add_trace(go.Bar(
        name="bota-fora",
        x=nomes,
        y=[r.volume_bota_fora for r in resultados],
        marker_color=CORES["bota_fora"],
    ))
    fig.add_trace(go.Bar(
        name="solo importado",
        x=nomes,
        y=[r.volume_solo_importado for r in resultados],
        marker_color=CORES["solo_imp"],
    ))

    _aplicar_layout(fig, titulo, height=440, barmode="group")
    return fig


def criar_perfil_faixa(
    perfil: dict,
    faixa: dict,
    titulo: str = "perfil da faixa",
) -> go.Figure:
    """Cria grafico de perfil (corte transversal) de uma faixa selecionada."""
    pos = perfil["posicoes"]
    terreno = perfil["terreno"]
    terreno_aj = perfil["terreno_ajustado"]
    projeto = perfil["projeto"]
    delta = perfil["delta"]

    direcao = faixa.get("direcao", "norte_sul")
    eixo_label = "easting (m)" if direcao == "norte_sul" else "northing (m)"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=pos, y=terreno,
        mode="lines",
        name="terreno natural",
        line=dict(color="#78716c", width=2),
    ))

    fig.add_trace(go.Scatter(
        x=pos, y=terreno_aj,
        mode="lines",
        name="terreno ajustado",
        line=dict(color="#a8a29e", width=1, dash="dash"),
    ))

    cota = float(projeto[0]) if len(projeto) > 0 else 0
    fig.add_trace(go.Scatter(
        x=pos, y=projeto,
        mode="lines",
        name="projeto ({:.2f}m)".format(cota),
        line=dict(color=CORES["accent"], width=2),
    ))

    corte_y = np.where(delta < 0, terreno_aj, projeto)
    fig.add_trace(go.Scatter(
        x=pos, y=corte_y,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=pos, y=projeto,
        fill="tonexty",
        fillcolor="rgba(225,29,72,0.12)",
        line=dict(width=0),
        name="corte",
    ))

    aterro_y = np.where(delta > 0, terreno_aj, projeto)
    fig.add_trace(go.Scatter(
        x=pos, y=projeto,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=pos, y=aterro_y,
        fill="tonexty",
        fillcolor="rgba(99,102,241,0.12)",
        line=dict(width=0),
        name="aterro",
    ))

    _aplicar_layout(fig, titulo, height=400,
                    xaxis_title=eixo_label,
                    yaxis_title="elev. (m)",
                    legend=dict(x=0.01, y=0.99))
    return fig
