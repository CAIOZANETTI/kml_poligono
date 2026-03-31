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
from modulos.tema import CORES

_TEMPLATE = "plotly_white"


# ── Helpers offset ──

def _offset_xy(superficie: SuperficieTerreno):
    """Retorna (x_min, y_min) para transformar coordenadas em relativas."""
    return float(superficie.grade_x.min()), float(superficie.grade_y.min())


# ── Mapa de contorno ──

def criar_mapa_contorno(
    superficie: SuperficieTerreno,
    titulo: str = "Curvas de Nivel",
    cota_projeto: Optional[float] = None,
    equidistancia: float = 1.0,
) -> go.Figure:
    """Cria mapa de curvas de nivel do terreno natural."""
    ox, oy = _offset_xy(superficie)

    fig = go.Figure(data=go.Contour(
        x=superficie.grade_x - ox,
        y=superficie.grade_y - oy,
        z=superficie.elevacao_malha,
        colorscale="Earth",
        contours=dict(
            showlabels=True,
            labelfont=dict(size=10, color="white"),
            size=equidistancia,
        ),
        colorbar=dict(title="Elev. (m)"),
    ))

    if cota_projeto is not None:
        fig.add_trace(go.Contour(
            x=superficie.grade_x - ox,
            y=superficie.grade_y - oy,
            z=superficie.elevacao_malha,
            contours=dict(
                type="constraint",
                operation="=",
                value=cota_projeto,
                showlabels=True,
                labelfont=dict(size=12, color="white"),
            ),
            line=dict(width=3, color="red"),
            showscale=False,
            name="Cota projeto ({:.2f} m)".format(cota_projeto),
            hoverinfo="name+z",
        ))

    fig.update_layout(
        title=titulo,
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
        yaxis_scaleanchor="x",
        template=_TEMPLATE,
        height=600,
    )
    return fig


# ── Helpers 3D ──

def _preparar_z_3d(
    elevacao_malha: np.ndarray,
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> tuple:
    """Prepara dados Z para visualizacao 3D."""
    if cota_referencia is not None:
        z_data = cota_referencia - elevacao_malha
        z_label = "Altura (m) [+ aterro / - corte]"
        colorscale = "RdBu"
        colorbar = dict(title="Altura (m)")
        if exagero_vertical > 1:
            z_data = z_data * exagero_vertical
            z_label += " ({}x)".format(exagero_vertical)
        return z_data, z_label, colorscale, colorbar
    else:
        z_data = elevacao_malha
        z_label = "Elev. (m)"
        if exagero_vertical > 1:
            z_media = float(np.nanmean(z_data))
            z_data = (z_data - z_media) * exagero_vertical + z_media
            z_label += " (exagero {}x)".format(exagero_vertical)
        return z_data, z_label, None, dict(title="Elev. (m)")


def _preparar_z_borda(
    borda_z: np.ndarray,
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
    z_media: Optional[float] = None,
) -> np.ndarray:
    """Aplica mesma transformacao Z nos pontos de borda."""
    if cota_referencia is not None:
        borda_z_out = cota_referencia - borda_z
        if exagero_vertical > 1:
            borda_z_out = borda_z_out * exagero_vertical
        return borda_z_out
    elif exagero_vertical > 1 and z_media is not None:
        return (borda_z - z_media) * exagero_vertical + z_media
    return borda_z


def criar_superficie_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "Terreno 3D",
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> go.Figure:
    """Cria visualizacao 3D do terreno natural."""
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    z_data, z_label, colorscale, colorbar = _preparar_z_3d(
        superficie.elevacao_malha, exagero_vertical, cota_referencia,
    )

    fig.add_trace(go.Surface(
        x=superficie.malha_x - ox,
        y=superficie.malha_y - oy,
        z=z_data,
        colorscale=colorscale or "Earth",
        colorbar=colorbar,
        name="Terreno",
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
            x=borda_fechada[:, 0] - ox,
            y=borda_fechada[:, 1] - oy,
            z=borda_z,
            mode="lines+markers",
            line=dict(color=CORES["borda"], width=3),
            marker=dict(size=2, color=CORES["borda"]),
            name="Borda",
        ))

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title=z_label,
            aspectmode="data",
        ),
        template=_TEMPLATE,
        height=700,
    )
    return fig


def criar_superficie_3d_contornos(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "Terreno 3D (Contornos)",
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> go.Figure:
    """Cria Surface 3D com contornos projetados no plano Z."""
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    z_data, z_label, colorscale, colorbar = _preparar_z_3d(
        superficie.elevacao_malha, exagero_vertical, cota_referencia,
    )

    fig.add_trace(go.Surface(
        x=superficie.malha_x - ox,
        y=superficie.malha_y - oy,
        z=z_data,
        colorscale=colorscale or "Viridis",
        colorbar=colorbar if colorscale else dict(title="Elev. (m)"),
        name="Terreno",
        connectgaps=True,
        contours_z=dict(
            show=True,
            usecolormap=True,
            highlightcolor="limegreen",
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
            x=borda_fechada[:, 0] - ox,
            y=borda_fechada[:, 1] - oy,
            z=borda_z,
            mode="lines+markers",
            line=dict(color=CORES["borda"], width=3),
            marker=dict(size=2, color=CORES["borda"]),
            name="Borda",
        ))

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title=z_label,
            aspectmode="data",
            camera=dict(eye=dict(x=1.87, y=0.88, z=-0.64)),
        ),
        template=_TEMPLATE,
        height=700,
        margin=dict(l=65, r=50, b=65, t=90),
    )
    return fig


def _triangular_grade(nrows, ncols):
    """Retorna indices de triangulos (i, j, k) para grade nrows x ncols."""
    r, c = np.meshgrid(np.arange(nrows - 1), np.arange(ncols - 1), indexing="ij")
    r = r.ravel()
    c = c.ravel()

    v00 = r * ncols + c
    v01 = r * ncols + c + 1
    v10 = (r + 1) * ncols + c
    v11 = (r + 1) * ncols + c + 1

    i_arr = np.concatenate([v00, v01])
    j_arr = np.concatenate([v01, v11])
    k_arr = np.concatenate([v10, v10])
    return i_arr, j_arr, k_arr


def _criar_solido_mesh3d(mx, my, z_terreno, cor, nome, mascara_face, opacidade=0.85):
    """Cria Mesh3d solido fechado (topo + base z=0 + paredes laterais).

    O solido e formado entre a superficie do terreno e o plano z=0.
    """
    nrows, ncols = mx.shape
    x_flat = mx.ravel().astype(float)
    y_flat = my.ravel().astype(float)
    z_flat = z_terreno.ravel().astype(float)
    n_verts = len(x_flat)

    i_all, j_all, k_all = _triangular_grade(nrows, ncols)

    # Remover triangulos com vertice NaN
    valid = (
        ~np.isnan(z_flat[i_all])
        & ~np.isnan(z_flat[j_all])
        & ~np.isnan(z_flat[k_all])
    )

    # Aplicar mascara de regiao (corte ou aterro)
    regiao = mascara_face[valid]
    i_top = i_all[valid][regiao]
    j_top = j_all[valid][regiao]
    k_top = k_all[valid][regiao]

    if len(i_top) == 0:
        return None

    # ── Vertices: terreno (0..n-1) + base em z=0 (n..2n-1) ──
    x_all = np.concatenate([x_flat, x_flat])
    y_all = np.concatenate([y_flat, y_flat])
    z_all = np.concatenate([z_flat, np.zeros_like(z_flat)])

    # ── Face superior: triangulos do terreno ──
    # (ja temos i_top, j_top, k_top)

    # ── Face inferior: mesmos triangulos em z=0, winding invertido ──
    i_bot = j_top + n_verts
    j_bot = i_top + n_verts
    k_bot = k_top + n_verts

    # ── Paredes laterais: arestas de contorno ──
    # Aresta de contorno = aparece em apenas 1 triangulo
    edges_a = np.stack([np.minimum(i_top, j_top), np.maximum(i_top, j_top)], axis=1)
    edges_b = np.stack([np.minimum(j_top, k_top), np.maximum(j_top, k_top)], axis=1)
    edges_c = np.stack([np.minimum(k_top, i_top), np.maximum(k_top, i_top)], axis=1)
    all_edges = np.vstack([edges_a, edges_b, edges_c])

    # Encontrar arestas unicas e suas contagens
    all_edges_sorted = all_edges[np.lexsort((all_edges[:, 1], all_edges[:, 0]))]
    # Comparar vizinhos para detectar duplicatas
    diff = np.any(all_edges_sorted[1:] != all_edges_sorted[:-1], axis=1)
    # Uma aresta e contorno se nao tem vizinho igual
    is_first = np.concatenate([[True], diff])
    is_last = np.concatenate([diff, [True]])
    boundary_mask = is_first & is_last
    boundary_edges = all_edges_sorted[boundary_mask]

    if len(boundary_edges) > 0:
        a = boundary_edges[:, 0]
        b = boundary_edges[:, 1]
        a2 = a + n_verts
        b2 = b + n_verts
        # Cada aresta de contorno → 2 triangulos (quad da parede)
        i_side = np.concatenate([a, b])
        j_side = np.concatenate([b, b2])
        k_side = np.concatenate([a2, a2])
    else:
        i_side = np.array([], dtype=int)
        j_side = np.array([], dtype=int)
        k_side = np.array([], dtype=int)

    # ── Combinar todas as faces ──
    i_final = np.concatenate([i_top, i_bot, i_side])
    j_final = np.concatenate([j_top, j_bot, j_side])
    k_final = np.concatenate([k_top, k_bot, k_side])

    return go.Mesh3d(
        x=x_all, y=y_all, z=z_all,
        i=i_final, j=j_final, k=k_final,
        color=cor,
        opacity=opacidade,
        name=nome,
        flatshading=False,
        lighting=dict(ambient=0.5, diffuse=0.9, specular=0.3, roughness=0.5),
        lightposition=dict(x=100, y=200, z=300),
        showlegend=True,
    )


def criar_corte_aterro_3d(
    superficie: SuperficieTerreno,
    cota_projeto: float,
    remocao_vegetal: float = 0.30,
    titulo: str = "Corte e Aterro 3D",
    opacidade_projeto: float = 0.5,
) -> go.Figure:
    """Cria visualizacao 3D de volumes solidos de corte e aterro.

    Cada regiao e um Mesh3d solido fechado (topo + base + paredes)
    entre a superficie do terreno e o plano de projeto (z=0).
    Vermelho = corte, Azul = aterro.
    """
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    mx = superficie.malha_x - ox
    my = superficie.malha_y - oy
    z_terreno = cota_projeto - superficie.elevacao_malha

    # ── Classificar cada face como corte ou aterro ──
    nrows, ncols = z_terreno.shape
    z_flat = z_terreno.ravel().astype(float)

    i_all, j_all, k_all = _triangular_grade(nrows, ncols)

    z_cent = (z_flat[i_all] + z_flat[j_all] + z_flat[k_all]) / 3.0
    mascara_aterro = z_cent >= 0
    mascara_corte = z_cent < 0

    # ── Solido Aterro (azul) ──
    trace_aterro = _criar_solido_mesh3d(
        mx, my, z_terreno, CORES["aterro"],
        "Aterro (+)", mascara_aterro, opacidade=0.85,
    )
    if trace_aterro is not None:
        fig.add_trace(trace_aterro)

    # ── Solido Corte (vermelho) ──
    trace_corte = _criar_solido_mesh3d(
        mx, my, z_terreno, CORES["corte"],
        "Corte (\u2212)", mascara_corte, opacidade=0.85,
    )
    if trace_corte is not None:
        fig.add_trace(trace_corte)

    # ── Plano de projeto (z = 0) transparente ──
    superficie_proj = gerar_superficie_projeto(superficie, cota_projeto)
    z_projeto = np.where(~np.isnan(superficie_proj), 0.0, np.nan)

    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_projeto,
        colorscale=[[0, "rgba(180,180,180,0.3)"], [1, "rgba(180,180,180,0.3)"]],
        opacity=opacidade_projeto,
        showscale=False,
        name="Plataforma de projeto",
        connectgaps=True,
    ))

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Altura (m) [+ aterro / \u2212 corte]",
            aspectmode="data",
        ),
        template=_TEMPLATE,
        height=700,
        legend=dict(
            x=0.01, y=0.99,
            bgcolor="rgba(255,255,255,0.8)",
        ),
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
    """Cria perfil transversal em uma posicao Y fixa."""
    pontos = superficie.pontos_grade_xy
    elevacoes = superficie.elevacao_grade
    ox = float(pontos[:, 0].min())

    if posicao_y is None:
        posicao_y = np.median(pontos[:, 1])

    tolerancia = grade.espacamento * 0.6
    mascara = np.abs(pontos[:, 1] - posicao_y) < tolerancia
    if mascara.sum() < 2:
        tolerancia = grade.espacamento * 1.5
        mascara = np.abs(pontos[:, 1] - posicao_y) < tolerancia

    xs = pontos[mascara, 0] - ox
    zs = elevacoes[mascara]
    ordem = np.argsort(xs)
    xs = xs[ordem]
    zs = zs[ordem]

    # Delta relativo a cota do projeto (+ aterro, - corte)
    zs_ajustado = zs - remocao_vegetal
    delta = cota_projeto - zs_ajustado

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=xs, y=delta, mode="lines", name="Delta (cota - terreno)",
        line=dict(color=CORES["terreno"], width=2),
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1,
                  annotation_text="Cota projeto")

    corte_y = np.where(delta < 0, delta, 0)
    aterro_y = np.where(delta > 0, delta, 0)

    fig.add_trace(go.Scatter(
        x=xs, y=corte_y, fill="tozeroy",
        fillcolor="rgba(225,29,72,0.15)", line=dict(width=0), name="Corte",
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=aterro_y, fill="tozeroy",
        fillcolor="rgba(99,102,241,0.15)", line=dict(width=0), name="Aterro",
    ))

    oy = float(superficie.pontos_grade_xy[:, 1].min())
    fig.update_layout(
        title="{} (Y = {:.1f}m)".format(titulo, posicao_y - oy),
        xaxis_title="X (m)",
        yaxis_title="Altura (m) [+ aterro / - corte]",
        template=_TEMPLATE,
        height=500,
        legend=dict(x=0.01, y=0.99),
    )
    return fig


def criar_diagrama_bruckner(
    resultado: ResultadoBruckner,
    titulo: str = "Diagrama de Bruckner",
    dlt: Optional[float] = None,
    posicao_destaque: Optional[float] = None,
) -> go.Figure:
    """Cria diagrama de Bruckner (curva de massa)."""
    fig = go.Figure()

    pos = resultado.posicoes
    # Offset para metros relativos
    pos_offset = pos - pos.min() if len(pos) > 0 else pos
    vol = resultado.volumes_acumulados

    fig.add_trace(go.Scatter(
        x=pos_offset, y=vol, mode="lines", name="Volume acumulado",
        line=dict(color=CORES["accent"], width=2),
    ))

    vol_pos = np.where(vol > 0, vol, 0)
    vol_neg = np.where(vol < 0, vol, 0)

    fig.add_trace(go.Scatter(
        x=pos_offset, y=vol_pos, fill="tozeroy",
        fillcolor="rgba(225,29,72,0.15)", line=dict(width=0), name="Bota-fora",
    ))
    fig.add_trace(go.Scatter(
        x=pos_offset, y=vol_neg, fill="tozeroy",
        fillcolor="rgba(99,102,241,0.15)", line=dict(width=0), name="Emprestimo",
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

    pos_min = pos.min() if len(pos) > 0 else 0
    for eq in resultado.pontos_equilibrio:
        fig.add_vline(
            x=eq - pos_min, line_dash="dot", line_color="green", line_width=1,
            annotation_text="{:.1f}m".format(eq - pos_min),
        )

    if dlt is not None:
        fig.add_hline(
            y=dlt, line_dash="dash", line_color="orange", line_width=2,
            annotation_text="DLT",
            annotation_position="top left",
        )

    if posicao_destaque is not None:
        pos_rel = posicao_destaque - pos_min
        fig.add_vline(
            x=pos_rel,
            line_color=CORES["aterro"],
            line_width=2,
            annotation_text="faixa selecionada",
            annotation_position="top right",
        )

    fig.update_layout(
        title=titulo,
        xaxis_title="Posicao (m)",
        yaxis_title="Volume acumulado (m\u00b3)",
        template=_TEMPLATE,
        height=500,
    )
    return fig


def criar_tabela_volumes(
    resultados: List[ResultadoVolume],
    titulo: str = "Resumo de volumes",
) -> go.Figure:
    """Cria tabela formatada com volumes."""
    headers = [
        "Poligono", "Area (m\u00b2)", "Corte bruto (m\u00b3)",
        "Aterro bruto (m\u00b3)", "Corte empolado (m\u00b3)",
        "Aterro compact. (m\u00b3)", "Bota-fora (m\u00b3)",
        "Solo import. (m\u00b3)", "Balanco (m\u00b3)",
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

    # Linha de totais
    valores[0].append("<b>TOTAL</b>")
    valores[1].append("<b>{:,.1f}</b>".format(sum(r.area_total for r in resultados)))
    valores[2].append("<b>{:,.2f}</b>".format(sum(r.volume_corte_bruto for r in resultados)))
    valores[3].append("<b>{:,.2f}</b>".format(sum(r.volume_aterro_bruto for r in resultados)))
    valores[4].append("<b>{:,.2f}</b>".format(sum(r.volume_corte_empolado for r in resultados)))
    valores[5].append("<b>{:,.2f}</b>".format(sum(r.volume_aterro_compactado for r in resultados)))
    valores[6].append("<b>{:,.2f}</b>".format(sum(r.volume_bota_fora for r in resultados)))
    valores[7].append("<b>{:,.2f}</b>".format(sum(r.volume_solo_importado for r in resultados)))
    valores[8].append("<b>{:,.2f}</b>".format(sum(r.balanco_massa for r in resultados)))

    n_linhas = len(resultados) + 1
    cores_linhas = [["#F5F5F5", "white"] * ((n_linhas + 1) // 2) for _ in headers]
    # Destaca ultima linha (totais) com azul claro
    for col in cores_linhas:
        if len(col) >= n_linhas:
            col[n_linhas - 1] = "#E3F2FD"

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color="#1565C0",
            font=dict(color="white", size=12),
            align="center",
        ),
        cells=dict(
            values=valores,
            fill_color=cores_linhas,
            align="center",
            font=dict(size=11),
        ),
    )])

    fig.update_layout(title=titulo, height=max(300, 100 + 40 * n_linhas))
    return fig


def criar_grafico_barras_volumes(
    resultados: List[ResultadoVolume],
    titulo: str = "Volumes por poligono",
) -> go.Figure:
    """Cria grafico de barras agrupadas."""
    nomes = [r.nome_poligono for r in resultados]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Corte empolado", x=nomes,
        y=[r.volume_corte_empolado for r in resultados],
        marker_color=CORES["corte"],
    ))
    fig.add_trace(go.Bar(
        name="Aterro compactado", x=nomes,
        y=[r.volume_aterro_compactado for r in resultados],
        marker_color=CORES["aterro"],
    ))
    fig.add_trace(go.Bar(
        name="Bota-fora", x=nomes,
        y=[r.volume_bota_fora for r in resultados],
        marker_color=CORES["bota_fora"],
    ))
    fig.add_trace(go.Bar(
        name="Solo importado", x=nomes,
        y=[r.volume_solo_importado for r in resultados],
        marker_color=CORES["solo_imp"],
    ))

    fig.update_layout(
        title=titulo,
        barmode="group",
        xaxis_title="Poligono",
        yaxis_title="Volume (m\u00b3)",
        template=_TEMPLATE,
        height=500,
    )
    return fig


def criar_perfil_faixa(
    perfil: dict,
    faixa: dict,
    titulo: str = "Perfil da Faixa",
) -> go.Figure:
    """Cria grafico de perfil de uma faixa selecionada."""
    pos = perfil["posicoes"]
    terreno = perfil["terreno"]
    terreno_aj = perfil["terreno_ajustado"]
    projeto = perfil["projeto"]
    delta = perfil["delta"]

    # Offset para metros relativos
    pos_offset = pos - pos.min() if len(pos) > 0 else pos

    direcao = faixa.get("direcao", "norte_sul")
    eixo_label = "X (m)" if direcao == "norte_sul" else "Y (m)"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=pos_offset, y=delta, mode="lines", name="Delta (cota - terreno)",
        line=dict(color=CORES["terreno"], width=2),
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1,
                  annotation_text="Cota projeto")

    corte_y = np.where(delta < 0, delta, 0)
    aterro_y = np.where(delta > 0, delta, 0)

    fig.add_trace(go.Scatter(
        x=pos_offset, y=corte_y, fill="tozeroy",
        fillcolor="rgba(225,29,72,0.15)", line=dict(width=0), name="Corte",
    ))
    fig.add_trace(go.Scatter(
        x=pos_offset, y=aterro_y, fill="tozeroy",
        fillcolor="rgba(99,102,241,0.15)", line=dict(width=0), name="Aterro",
    ))

    fig.update_layout(
        title=titulo,
        xaxis_title=eixo_label,
        yaxis_title="Altura (m) [+ aterro / - corte]",
        template=_TEMPLATE,
        height=450,
        legend=dict(x=0.01, y=0.99),
    )
    return fig
