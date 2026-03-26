"""Visualizacoes Plotly para terraplenagem."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional

from modulos.terreno import SuperficieTerreno, gerar_superficie_projeto
from modulos.volumes import ResultadoVolume
from modulos.bruckner import ResultadoBruckner
from modulos.geometria import GradePoligono


def criar_mapa_contorno(
    superficie: SuperficieTerreno,
    titulo: str = "Curvas de N\u00edvel",
) -> go.Figure:
    """Cria mapa de curvas de nivel do terreno natural."""
    fig = go.Figure(data=go.Contour(
        x=superficie.grade_x,
        y=superficie.grade_y,
        z=superficie.elevacao_malha,
        colorscale="Earth",
        contours=dict(
            showlabels=True,
            labelfont=dict(size=10, color="white"),
        ),
        colorbar=dict(title="Eleva\u00e7\u00e3o (m)"),
    ))

    fig.update_layout(
        title=titulo,
        xaxis_title="Easting (m)",
        yaxis_title="Northing (m)",
        yaxis_scaleanchor="x",
        template="plotly_white",
        height=600,
    )
    return fig


def criar_superficie_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "Terreno Natural 3D",
) -> go.Figure:
    """Cria visualizacao 3D do terreno natural."""
    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=superficie.elevacao_malha,
        colorscale="Earth",
        colorbar=dict(title="Eleva\u00e7\u00e3o (m)"),
        name="Terreno Natural",
    ))

    # Adiciona contorno da borda
    if grade is not None:
        borda = grade.pontos_borda
        # Fecha o poligono
        borda_fechada = np.vstack([borda, borda[0:1]])
        fig.add_trace(go.Scatter3d(
            x=borda_fechada[:, 0],
            y=borda_fechada[:, 1],
            z=borda_fechada[:, 2],
            mode="lines+markers",
            line=dict(color="red", width=4),
            marker=dict(size=3, color="red"),
            name="Borda do Pol\u00edgono",
        ))

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Easting (m)",
            yaxis_title="Northing (m)",
            zaxis_title="Eleva\u00e7\u00e3o (m)",
            aspectmode="data",
        ),
        template="plotly_white",
        height=700,
    )
    return fig


def criar_comparacao_3d(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    remocao_vegetal: float = 0.30,
    titulo: str = "Terreno Natural vs Projeto",
) -> go.Figure:
    """Cria visualizacao 3D comparando terreno com superficie de projeto."""
    fig = go.Figure()

    # Terreno natural
    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=superficie.elevacao_malha,
        colorscale="Earth",
        opacity=0.8,
        name="Terreno Natural",
        showscale=False,
    ))

    # Superficie de projeto (plana)
    superficie_proj = gerar_superficie_projeto(superficie, cota_projeto)
    fig.add_trace(go.Surface(
        x=superficie.malha_x,
        y=superficie.malha_y,
        z=superficie_proj,
        colorscale=[[0, "rgba(30,136,229,0.4)"], [1, "rgba(30,136,229,0.4)"]],
        showscale=False,
        name=f"Projeto (cota {cota_projeto:.2f}m)",
    ))

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Easting (m)",
            yaxis_title="Northing (m)",
            zaxis_title="Eleva\u00e7\u00e3o (m)",
            aspectmode="data",
        ),
        template="plotly_white",
        height=700,
    )
    return fig


def criar_mapa_corte_aterro(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    remocao_vegetal: float = 0.30,
    titulo: str = "Mapa de Corte e Aterro",
) -> go.Figure:
    """Cria mapa 2D com zonas de corte (vermelho) e aterro (azul)."""
    terreno_ajustado = superficie.elevacao_malha - remocao_vegetal
    delta = cota_projeto - terreno_ajustado

    # Limita escala simetrica
    vmax = max(abs(np.nanmin(delta)), abs(np.nanmax(delta)))

    fig = go.Figure(data=go.Heatmap(
        x=superficie.grade_x,
        y=superficie.grade_y,
        z=delta,
        colorscale="RdBu",
        zmid=0,
        zmin=-vmax,
        zmax=vmax,
        colorbar=dict(title="Delta (m)<br>+ Aterro / - Corte"),
    ))

    fig.update_layout(
        title=titulo,
        xaxis_title="Easting (m)",
        yaxis_title="Northing (m)",
        yaxis_scaleanchor="x",
        template="plotly_white",
        height=600,
    )
    return fig


def criar_perfil_transversal(
    superficie: SuperficieTerreno,
    grade: GradePoligono,
    cota_projeto: float,
    posicao_y: Optional[float] = None,
    remocao_vegetal: float = 0.30,
    talude_corte: tuple = (1, 1),
    talude_aterro: tuple = (1, 2),
    titulo: str = "Perfil Transversal",
) -> go.Figure:
    """Cria perfil transversal (corte) em uma posicao Y fixa."""
    pontos = superficie.pontos_grade_xy
    elevacoes = superficie.elevacao_grade

    if posicao_y is None:
        posicao_y = np.median(pontos[:, 1])

    # Encontra pontos mais proximos da posicao Y
    tolerancia = grade.espacamento * 0.6
    mascara = np.abs(pontos[:, 1] - posicao_y) < tolerancia
    if mascara.sum() < 2:
        # Aumenta tolerancia
        tolerancia = grade.espacamento * 1.5
        mascara = np.abs(pontos[:, 1] - posicao_y) < tolerancia

    xs = pontos[mascara, 0]
    zs = elevacoes[mascara]

    # Ordena por X
    ordem = np.argsort(xs)
    xs = xs[ordem]
    zs = zs[ordem]

    fig = go.Figure()

    # Terreno natural
    fig.add_trace(go.Scatter(
        x=xs, y=zs,
        mode="lines",
        name="Terreno Natural",
        line=dict(color="#8B4513", width=2),
        fill="tozeroy",
        fillcolor="rgba(139,69,19,0.1)",
    ))

    # Terreno ajustado (sem vegetal)
    zs_ajustado = zs - remocao_vegetal
    fig.add_trace(go.Scatter(
        x=xs, y=zs_ajustado,
        mode="lines",
        name=f"Terreno (-{remocao_vegetal}m vegetal)",
        line=dict(color="#A0522D", width=1, dash="dash"),
    ))

    # Linha do projeto
    fig.add_trace(go.Scatter(
        x=[xs[0], xs[-1]],
        y=[cota_projeto, cota_projeto],
        mode="lines",
        name=f"Projeto ({cota_projeto:.2f}m)",
        line=dict(color="#1E88E5", width=3),
    ))

    # Zonas de corte e aterro com preenchimento
    delta = cota_projeto - zs_ajustado
    corte_y = np.where(delta < 0, zs_ajustado, cota_projeto)
    aterro_y = np.where(delta > 0, zs_ajustado, cota_projeto)

    fig.add_trace(go.Scatter(
        x=xs, y=corte_y,
        fill="tonexty",
        fillcolor="rgba(198,40,40,0.3)",
        line=dict(width=0),
        name="Corte",
        showlegend=True,
    ))

    fig.add_trace(go.Scatter(
        x=xs, y=aterro_y,
        fill="tonexty",
        fillcolor="rgba(30,136,229,0.3)",
        line=dict(width=0),
        name="Aterro",
        showlegend=True,
    ))

    fig.update_layout(
        title=f"{titulo} (Y = {posicao_y:.1f}m)",
        xaxis_title="Easting (m)",
        yaxis_title="Eleva\u00e7\u00e3o (m)",
        template="plotly_white",
        height=500,
        legend=dict(x=0.01, y=0.99),
    )
    return fig


def criar_diagrama_bruckner(
    resultado: ResultadoBruckner,
    titulo: str = "Diagrama de Br\u00fcckner",
) -> go.Figure:
    """Cria diagrama de Bruckner (curva de massa)."""
    fig = go.Figure()

    pos = resultado.posicoes
    vol = resultado.volumes_acumulados

    # Curva de massa
    fig.add_trace(go.Scatter(
        x=pos, y=vol,
        mode="lines",
        name="Volume Acumulado",
        line=dict(color="#1565C0", width=3),
    ))

    # Preenchimento: positivo (bota-fora) e negativo (emprestimo)
    vol_pos = np.where(vol > 0, vol, 0)
    vol_neg = np.where(vol < 0, vol, 0)

    fig.add_trace(go.Scatter(
        x=pos, y=vol_pos,
        fill="tozeroy",
        fillcolor="rgba(198,40,40,0.2)",
        line=dict(width=0),
        name="Bota-fora",
    ))

    fig.add_trace(go.Scatter(
        x=pos, y=vol_neg,
        fill="tozeroy",
        fillcolor="rgba(30,136,229,0.2)",
        line=dict(width=0),
        name="Empr\u00e9stimo",
    ))

    # Linha zero
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

    # Pontos de equilibrio
    for eq in resultado.pontos_equilibrio:
        fig.add_vline(
            x=eq, line_dash="dot", line_color="green", line_width=1,
            annotation_text=f"Eq: {eq:.1f}m",
        )

    fig.update_layout(
        title=titulo,
        xaxis_title="Posi\u00e7\u00e3o (m)",
        yaxis_title="Volume Acumulado (m\u00b3)",
        template="plotly_white",
        height=500,
    )
    return fig


def criar_tabela_volumes(
    resultados: List[ResultadoVolume],
    titulo: str = "Resumo de Volumes",
) -> go.Figure:
    """Cria tabela formatada com volumes de corte e aterro."""
    headers = [
        "Pol\u00edgono", "\u00c1rea (m\u00b2)", "Corte Bruto (m\u00b3)",
        "Aterro Bruto (m\u00b3)", "Corte Empolado (m\u00b3)",
        "Aterro Compactado (m\u00b3)", "Bota-fora (m\u00b3)",
        "Solo Import. (m\u00b3)", "Balan\u00e7o (m\u00b3)",
    ]

    valores = [[] for _ in headers]
    for r in resultados:
        valores[0].append(r.nome_poligono)
        valores[1].append(f"{r.area_total:,.1f}")
        valores[2].append(f"{r.volume_corte_bruto:,.2f}")
        valores[3].append(f"{r.volume_aterro_bruto:,.2f}")
        valores[4].append(f"{r.volume_corte_empolado:,.2f}")
        valores[5].append(f"{r.volume_aterro_compactado:,.2f}")
        valores[6].append(f"{r.volume_bota_fora:,.2f}")
        valores[7].append(f"{r.volume_solo_importado:,.2f}")
        valores[8].append(f"{r.balanco_massa:,.2f}")

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color="#1565C0",
            font=dict(color="white", size=12),
            align="center",
        ),
        cells=dict(
            values=valores,
            fill_color=[["#F5F5F5", "white"] * ((len(resultados) + 1) // 2)] * len(headers),
            align="center",
            font=dict(size=11),
        ),
    )])

    fig.update_layout(title=titulo, height=max(300, 100 + 40 * len(resultados)))
    return fig


def criar_grafico_barras_volumes(
    resultados: List[ResultadoVolume],
    titulo: str = "Volumes por Pol\u00edgono",
) -> go.Figure:
    """Cria grafico de barras agrupadas com volumes por poligono."""
    nomes = [r.nome_poligono for r in resultados]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Corte Empolado",
        x=nomes,
        y=[r.volume_corte_empolado for r in resultados],
        marker_color="#C62828",
    ))
    fig.add_trace(go.Bar(
        name="Aterro Compactado",
        x=nomes,
        y=[r.volume_aterro_compactado for r in resultados],
        marker_color="#1565C0",
    ))
    fig.add_trace(go.Bar(
        name="Bota-fora",
        x=nomes,
        y=[r.volume_bota_fora for r in resultados],
        marker_color="#EF6C00",
    ))
    fig.add_trace(go.Bar(
        name="Solo Importado",
        x=nomes,
        y=[r.volume_solo_importado for r in resultados],
        marker_color="#2E7D32",
    ))

    fig.update_layout(
        title=titulo,
        barmode="group",
        xaxis_title="Pol\u00edgono",
        yaxis_title="Volume (m\u00b3)",
        template="plotly_white",
        height=500,
    )
    return fig
