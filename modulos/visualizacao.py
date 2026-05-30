"""Visualizacoes Plotly para terraplenagem."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional

from modulos.terreno import SuperficieTerreno
from modulos.volumes import ResultadoVolume
from modulos.bruckner import ResultadoBruckner
from modulos.geometria import GradePoligono
from modulos.tema import CORES

_TEMPLATE = "plotly_white"


# Escala corte/aterro: azul (aterro, abaixo do projeto) → branco → vermelho (corte, acima)
_ESCALA_CORTE_ATERRO = [
    [0.0, CORES["aterro"]],
    [0.5, "#f7f7f7"],
    [1.0, CORES["corte"]],
]


# ── Helpers offset ──

def _offset_xy(superficie: SuperficieTerreno):
    """Retorna (x_min, y_min) para transformar coordenadas em relativas."""
    return float(superficie.grade_x.min()), float(superficie.grade_y.min())


# ── Indicacao de norte ──
# Coordenadas em UTM: X = Easting (Leste), Y = Northing (Norte).
# Logo o eixo Y aponta para o norte verdadeiro.

def _anotacao_norte_2d(fig: go.Figure) -> None:
    """Adiciona seta de norte (para cima) no canto do grafico 2D."""
    fig.add_annotation(
        x=0.98, y=0.97, xref="paper", yref="paper",
        text="<b>N</b>", showarrow=True, arrowhead=2,
        arrowsize=1.2, arrowwidth=2, arrowcolor="#444",
        ax=0, ay=36, font=dict(size=14, color="#444"),
    )


def _arrow_norte_3d(fig: go.Figure, mx, my, z_level: float) -> None:
    """Seta de norte 3D apontando para +Y (= norte geografico em UTM).

    Desenhada com haste e ponta de flecha vermelhas para nao se confundir
    com outras linhas da cena; gira junto com a camera.
    """
    x0 = float(np.nanmax(mx))
    y_min, y_max = float(np.nanmin(my)), float(np.nanmax(my))
    L = 0.15 * (y_max - y_min)
    y_tip = y_min + L
    aw = 0.22 * L   # meia-largura da ponta
    ah = 0.28 * L   # comprimento da ponta
    # Haste + ponta (em "V") num unico traco, com None separando os segmentos
    fig.add_trace(go.Scatter3d(
        x=[x0, x0, None, x0 - aw, x0, x0 + aw],
        y=[y_min, y_tip, None, y_tip - ah, y_tip, y_tip - ah],
        z=[z_level, z_level, None, z_level, z_level, z_level],
        mode="lines", line=dict(color="#c0392b", width=6),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[x0], y=[y_tip + 0.18 * L], z=[z_level], mode="text",
        text=["N"], textfont=dict(size=16, color="#c0392b"),
        hoverinfo="skip", showlegend=False,
    ))


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
        xaxis_title="Leste (m)",
        yaxis_title="Norte (m)",
        yaxis_scaleanchor="x",
        template=_TEMPLATE,
        height=600,
    )
    _anotacao_norte_2d(fig)
    return fig


# ── Helpers 3D ──

def _passo_decimacao(n: int, alvo: int = 140) -> int:
    """Passo de stride para limitar a malha a ~alvo celulas por eixo."""
    return max(1, int(np.ceil(n / alvo)))


def _decimar(*arrays: np.ndarray, alvo: int = 140):
    """Reduz malhas 2D por stride (NumPy) preservando regularidade."""
    base = arrays[0]
    sl = (
        slice(None, None, _passo_decimacao(base.shape[0], alvo)),
        slice(None, None, _passo_decimacao(base.shape[1], alvo)),
    )
    return [None if a is None else a[sl] for a in arrays]


def _plano_projeto(mx, my, z_mascara, cota: float, opacidade: float):
    """Plataforma de projeto recortada ao poligono (plano horizontal na cota).

    Usa a mascara de NaN do terreno para nao vazar para fora do lote.
    """
    z = np.where(~np.isnan(z_mascara), float(cota), np.nan)
    return go.Surface(
        x=mx, y=my, z=z,
        colorscale=[[0, "rgba(140,140,140,1)"], [1, "rgba(140,140,140,1)"]],
        opacity=opacidade,
        showscale=False,
        name="Plataforma de projeto",
        connectgaps=False,
        hoverinfo="name",
        lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0),
    )


def _contorno_intersecao(z_terreno: np.ndarray, cota: float) -> dict:
    """Contorno em z=cota: a linha onde o plano de projeto corta o terreno."""
    zmin = float(np.nanmin(z_terreno))
    zmax = float(np.nanmax(z_terreno))
    return dict(z=dict(
        show=True,
        start=float(cota), end=float(cota),
        size=max(zmax - zmin, 1.0),
        color="#111111", width=3,
        usecolormap=False,
    ))


def _aspecto_cena(mx: np.ndarray, my: np.ndarray, exagero_vertical: int) -> dict:
    """Aspecto manual: horizontal em escala real, vertical exagerado p/ visual."""
    dx = float(np.nanmax(mx) - np.nanmin(mx)) or 1.0
    dy = float(np.nanmax(my) - np.nanmin(my)) or 1.0
    dmax = max(dx, dy)
    return dict(x=dx / dmax, y=dy / dmax, z=0.18 * float(exagero_vertical))


def _criar_terreno_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono],
    titulo: str,
    exagero_vertical: int,
    cota_referencia: Optional[float],
    contornos: bool,
) -> go.Figure:
    """Terreno 3D em elevacao real, colorido por corte/aterro relativo a cota.

    Mostra o relevo verdadeiro (coordenadas nao distorcidas). O exagero
    vertical e apenas visual (aspecto da cena). A plataforma de projeto e
    um plano horizontal independente na cota desejada. A malha e decimada
    para renderizar rapido em grades densas.
    """
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    mx_full = superficie.malha_x - ox
    my_full = superficie.malha_y - oy
    z_full = superficie.elevacao_malha

    if cota_referencia is not None:
        delta_full = z_full - cota_referencia  # >0 corte, <0 aterro
    else:
        delta_full = None

    mx, my, z_terreno, delta = _decimar(mx_full, my_full, z_full, delta_full)

    # Cor por corte (terreno acima do projeto, +) / aterro (abaixo, -)
    if cota_referencia is not None:
        maxabs = float(np.nanmax(np.abs(delta))) or 1.0
        cor_kwargs = dict(
            surfacecolor=delta,
            colorscale=_ESCALA_CORTE_ATERRO,
            cmin=-maxabs, cmid=0.0, cmax=maxabs,
            colorbar=dict(title="Corte (+) / Aterro (−) (m)", thickness=14),
        )
        # Linha de intersecao plano x terreno (divisa corte/aterro)
        contour_kwargs = dict(contours=_contorno_intersecao(z_terreno, cota_referencia))
    else:
        cor_kwargs = dict(colorscale="Earth", colorbar=dict(title="Elev. (m)", thickness=14))
        contour_kwargs = {}

    # connectgaps=False: respeita a borda do poligono (sem costurar buracos)
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_terreno,
        name="Terreno",
        connectgaps=False,
        lighting=dict(ambient=0.65, diffuse=0.85, roughness=0.6, specular=0.15),
        **cor_kwargs,
        **contour_kwargs,
    ))

    # Plataforma de projeto: plano horizontal recortado ao poligono, na cota
    if cota_referencia is not None:
        fig.add_trace(_plano_projeto(mx, my, z_terreno, cota_referencia, opacidade=0.30))

    if grade is not None:
        borda = grade.pontos_borda
        borda_fechada = np.vstack([borda, borda[0:1]])
        fig.add_trace(go.Scatter3d(
            x=borda_fechada[:, 0] - ox,
            y=borda_fechada[:, 1] - oy,
            z=borda_fechada[:, 2],
            mode="lines",
            line=dict(color=CORES["borda"], width=3),
            name="Borda",
        ))

    _arrow_norte_3d(fig, mx, my, float(np.nanmin(z_terreno)))

    z_label = "Elevação (m)"
    if exagero_vertical > 1:
        z_label += " · exagero visual {}x".format(exagero_vertical)

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Leste (m)",
            yaxis_title="Norte (m)",
            zaxis_title=z_label,
            aspectmode="manual",
            aspectratio=_aspecto_cena(mx, my, exagero_vertical),
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.85)),
        ),
        template=_TEMPLATE,
        height=700,
        margin=dict(l=40, r=20, b=40, t=70),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def criar_superficie_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "Terreno 3D",
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> go.Figure:
    """Visualizacao 3D do terreno natural (sem contornos projetados)."""
    return _criar_terreno_3d(
        superficie, grade, titulo, exagero_vertical, cota_referencia,
        contornos=False,
    )


def criar_superficie_3d_contornos(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    titulo: str = "Terreno 3D (Contornos)",
    exagero_vertical: int = 1,
    cota_referencia: Optional[float] = None,
) -> go.Figure:
    """Surface 3D com contornos projetados no plano Z."""
    return _criar_terreno_3d(
        superficie, grade, titulo, exagero_vertical, cota_referencia,
        contornos=True,
    )


def criar_plataforma_projeto_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    cota_projeto: float = 0.0,
    titulo: str = "Plataforma de Projeto",
    exagero_vertical: int = 1,
) -> go.Figure:
    """Mostra o ESTADO DESEJADO: a plataforma plana (terreno terraplanado)
    na cota de projeto, com o terreno natural por tras como referencia.
    """
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    mx, my, z_terreno = _decimar(
        superficie.malha_x - ox,
        superficie.malha_y - oy,
        superficie.elevacao_malha.astype(float),
    )

    # Terreno natural como referencia translucida (fantasma)
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_terreno,
        colorscale=[[0, "rgba(120,120,120,1)"], [1, "rgba(120,120,120,1)"]],
        opacity=0.18, showscale=False, name="Terreno natural",
        connectgaps=False, hoverinfo="name",
        lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0),
    ))

    # Plataforma plana desejada: superficie solida na cota, recortada ao lote
    z_plat = np.where(~np.isnan(z_terreno), float(cota_projeto), np.nan)
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_plat,
        colorscale=[[0, CORES["accent"]], [1, CORES["accent"]]],
        opacity=0.95, showscale=False, name="Plataforma de projeto",
        connectgaps=False, hoverinfo="name",
        lighting=dict(ambient=0.8, diffuse=0.5, specular=0.1),
    ))

    if grade is not None:
        borda = grade.pontos_borda
        borda_fechada = np.vstack([borda, borda[0:1]])
        fig.add_trace(go.Scatter3d(
            x=borda_fechada[:, 0] - ox,
            y=borda_fechada[:, 1] - oy,
            z=np.full(len(borda_fechada), float(cota_projeto)),
            mode="lines",
            line=dict(color=CORES["borda"], width=3),
            name="Contorno do lote",
        ))

    _arrow_norte_3d(fig, mx, my, float(np.nanmin(z_terreno)))

    z_label = "Elevação (m)"
    if exagero_vertical > 1:
        z_label += " · exagero visual {}x".format(exagero_vertical)

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Leste (m)",
            yaxis_title="Norte (m)",
            zaxis_title=z_label,
            aspectmode="manual",
            aspectratio=_aspecto_cena(mx, my, exagero_vertical),
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.85)),
        ),
        template=_TEMPLATE,
        height=700,
        margin=dict(l=40, r=20, b=40, t=70),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


_COR_GREIDE = "#9aa3ab"  # cinza concreto do greide acabado


def _skirt_taludes(grade, cota: float, ox: float, oy: float,
                   ratio_corte: float, ratio_aterro: float):
    """Saias de talude do greide: liga a aresta do plato (na cota) ao terreno.

    Para cada vertice da borda, projeta um ponto de offset (daylight) para
    fora do lote, a uma distancia = altura * (H/V), na elevacao natural.
    Constroi uma tira (Mesh3d) entre o anel interno (cota) e o externo.
    """
    borda = grade.pontos_borda
    if borda is None or len(borda) < 3:
        return None

    xy = borda[:, :2].astype(float)
    ez = borda[:, 2].astype(float)
    centro = xy.mean(axis=0)
    fora = xy - centro
    norma = np.linalg.norm(fora, axis=1, keepdims=True)
    norma[norma == 0] = 1.0
    fora = fora / norma

    dh = ez - cota                                    # >0 corte, <0 aterro
    run = np.where(dh > 0, dh * ratio_corte, -dh * ratio_aterro)

    inner = np.column_stack([xy[:, 0] - ox, xy[:, 1] - oy, np.full(len(xy), float(cota))])
    outer = np.column_stack([xy[:, 0] - ox + fora[:, 0] * run,
                             xy[:, 1] - oy + fora[:, 1] * run, ez])

    n = len(inner)
    verts = np.vstack([inner, outer])
    i_idx, j_idx, k_idx = [], [], []
    for s in range(n):
        a, b = s, (s + 1) % n
        c, d = b + n, s + n
        i_idx += [a, a]
        j_idx += [b, c]
        k_idx += [c, d]

    return go.Mesh3d(
        x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
        i=i_idx, j=j_idx, k=k_idx,
        color=_COR_GREIDE, opacity=0.95, name="Taludes",
        flatshading=True, showlegend=True,
        lighting=dict(ambient=0.7, diffuse=0.5, specular=0.05),
    )


def criar_terreno_greide_3d(
    superficie: SuperficieTerreno,
    grade: Optional[GradePoligono] = None,
    cota_projeto: float = 0.0,
    talude_corte_h: float = 1.0,
    talude_corte_v: float = 1.0,
    talude_aterro_h: float = 2.0,
    talude_aterro_v: float = 1.0,
    titulo: str = "Terreno e Greide de Projeto",
    exagero_vertical: int = 1,
) -> go.Figure:
    """Vista unificada: Terreno Existente (EG) x Greide de Projeto (FG).

    - EG: terreno natural translucido, colorido por corte/aterro, com a
      linha de interseccao na cota.
    - FG: o greide solido = plato plano na cota + saias de talude que
      amarram no terreno natural nas bordas.
    """
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    z_full = superficie.elevacao_malha.astype(float)
    mx, my, z_eg, delta = _decimar(
        superficie.malha_x - ox, superficie.malha_y - oy,
        z_full, z_full - float(cota_projeto),
    )
    maxabs = float(np.nanmax(np.abs(delta))) or 1.0

    # ── EG: terreno existente (translucido, corte/aterro) ──
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_eg, surfacecolor=delta,
        colorscale=_ESCALA_CORTE_ATERRO, cmin=-maxabs, cmid=0.0, cmax=maxabs,
        opacity=0.5, name="Terreno existente",
        colorbar=dict(title="Corte (+) / Aterro (−) (m)", thickness=14),
        connectgaps=False,
        contours=_contorno_intersecao(z_eg, cota_projeto),
        hoverinfo="x+y+z",
    ))

    # ── FG: plato plano (greide) na cota, recortado ao lote ──
    z_pad = np.where(~np.isnan(z_eg), float(cota_projeto), np.nan)
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_pad,
        colorscale=[[0, _COR_GREIDE], [1, _COR_GREIDE]], showscale=False,
        opacity=0.95, name="Greide (plato)", connectgaps=False, hoverinfo="name",
        lighting=dict(ambient=0.8, diffuse=0.4, specular=0.05),
    ))

    # ── FG: saias de talude + borda do plato ──
    if grade is not None:
        skirt = _skirt_taludes(
            grade, float(cota_projeto), ox, oy,
            talude_corte_h / talude_corte_v,
            talude_aterro_h / talude_aterro_v,
        )
        if skirt is not None:
            fig.add_trace(skirt)
        borda = grade.pontos_borda
        bf = np.vstack([borda, borda[0:1]])
        fig.add_trace(go.Scatter3d(
            x=bf[:, 0] - ox, y=bf[:, 1] - oy,
            z=np.full(len(bf), float(cota_projeto)),
            mode="lines", line=dict(color=CORES["borda"], width=3),
            name="Borda do plato",
        ))

    _arrow_norte_3d(fig, mx, my, float(np.nanmin(z_eg)))

    z_label = "Elevação (m)"
    if exagero_vertical > 1:
        z_label += " · exagero visual {}x".format(exagero_vertical)

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Leste (m)",
            yaxis_title="Norte (m)",
            zaxis_title=z_label,
            aspectmode="manual",
            aspectratio=_aspecto_cena(mx, my, exagero_vertical),
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.85)),
        ),
        template=_TEMPLATE,
        height=720,
        margin=dict(l=40, r=20, b=40, t=70),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


_COR_TALUDE_CORTE = "#e07b54"   # laranja terroso (corte)
_COR_TALUDE_ATERRO = "#5b9bd5"  # azul (aterro)


def _mesh_strip(inner, outer, seg_mask, cor, nome, ox, oy):
    """Tira triangulada (Mesh3d) entre o anel interno e o externo dos taludes."""
    n = len(inner)
    idx = np.where(seg_mask)[0]
    if len(idx) == 0:
        return None
    vx, vy, vz = [], [], []
    fi, fj, fk = [], [], []
    for s in idx:
        t = (s + 1) % n
        quad = [inner[s], inner[t], outer[t], outer[s]]
        base = len(vx)
        for p in quad:
            vx.append(p[0] - ox)
            vy.append(p[1] - oy)
            vz.append(p[2])
        fi += [base, base]
        fj += [base + 1, base + 2]
        fk += [base + 2, base + 3]
    return go.Mesh3d(
        x=vx, y=vy, z=vz, i=fi, j=fj, k=fk,
        color=cor, opacity=0.9, name=nome, flatshading=True, showlegend=True,
        lighting=dict(ambient=0.75, diffuse=0.5, specular=0.05),
        hoverinfo="name",
    )


def criar_greide_3d(
    superficie: SuperficieTerreno,
    grade: GradePoligono,
    taludes,
    cota_projeto: float = 0.0,
    titulo: str = "Greide de Projeto",
    exagero_vertical: int = 1,
) -> go.Figure:
    """Vista 3D com elementos SEPARADOS (ligaveis na legenda):

    terreno natural, plato, talude de corte, talude de aterro, linha de
    daylight (offset alem da divisa) e borda do plato. ``taludes`` e um
    ``TaludesResolvidos`` de ``modulos.greide``.
    """
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    z_full = superficie.elevacao_malha.astype(float)
    mx, my, z_eg, delta = _decimar(
        superficie.malha_x - ox, superficie.malha_y - oy,
        z_full, z_full - float(cota_projeto),
    )
    maxabs = float(np.nanmax(np.abs(delta))) or 1.0

    # 1) Terreno natural (translucido, corte/aterro)
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_eg, surfacecolor=delta,
        colorscale=_ESCALA_CORTE_ATERRO, cmin=-maxabs, cmid=0.0, cmax=maxabs,
        opacity=0.45, name="Terreno natural", showscale=False,
        connectgaps=False, contours=_contorno_intersecao(z_eg, cota_projeto),
        hoverinfo="x+y+z",
    ))

    # 2) Plato plano na cota, recortado ao lote
    z_pad = np.where(~np.isnan(z_eg), float(cota_projeto), np.nan)
    fig.add_trace(go.Surface(
        x=mx, y=my, z=z_pad,
        colorscale=[[0, _COR_GREIDE], [1, _COR_GREIDE]], showscale=False,
        opacity=0.95, name="Platô", connectgaps=False, hoverinfo="name",
        lighting=dict(ambient=0.85, diffuse=0.35, specular=0.05),
    ))

    # 3+4) Taludes de corte e de aterro (meshes separados)
    inner, outer = taludes.inner, taludes.outer
    dh = taludes.dh
    n = len(inner)
    dh_mid = 0.5 * (dh + np.roll(dh, -1))   # dh no meio de cada segmento
    ativo = (taludes.is_corte | taludes.is_aterro)
    seg_ativo = ativo & np.roll(ativo, -1)
    seg_corte = seg_ativo & (dh_mid > 0)
    seg_aterro = seg_ativo & (dh_mid < 0)

    m_corte = _mesh_strip(inner, outer, seg_corte, _COR_TALUDE_CORTE,
                          "Talude de corte", ox, oy)
    m_aterro = _mesh_strip(inner, outer, seg_aterro, _COR_TALUDE_ATERRO,
                           "Talude de aterro", ox, oy)
    if m_corte is not None:
        fig.add_trace(m_corte)
    if m_aterro is not None:
        fig.add_trace(m_aterro)

    # 5) Linha de daylight (limite da terraplenagem, alem da divisa)
    off = np.vstack([outer, outer[0:1]])
    fig.add_trace(go.Scatter3d(
        x=off[:, 0] - ox, y=off[:, 1] - oy, z=off[:, 2],
        mode="lines", line=dict(color="#444", width=4, dash="dot"),
        name="Linha de daylight (offset)",
    ))

    # 6) Borda do plato (na cota)
    ring = np.vstack([inner, inner[0:1]])
    fig.add_trace(go.Scatter3d(
        x=ring[:, 0] - ox, y=ring[:, 1] - oy, z=ring[:, 2],
        mode="lines", line=dict(color=CORES["borda"], width=3),
        name="Borda do platô",
    ))

    _arrow_norte_3d(fig, mx, my, float(np.nanmin(z_eg)))

    z_label = "Elevação (m)"
    if exagero_vertical > 1:
        z_label += " · exagero visual {}x".format(exagero_vertical)

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Leste (m)", yaxis_title="Norte (m)", zaxis_title=z_label,
            aspectmode="manual",
            aspectratio=_aspecto_cena(mx, my, exagero_vertical),
            camera=dict(eye=dict(x=1.6, y=-1.6, z=0.9)),
        ),
        template=_TEMPLATE, height=740,
        margin=dict(l=40, r=20, b=40, t=70),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
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


def _criar_solido_mesh3d(mx, my, z_terreno, cor, nome, mascara_face,
                         opacidade=0.85, z_base=0.0):
    """Cria Mesh3d solido fechado (topo + base + paredes laterais).

    O solido e formado entre a superficie do terreno e o plano horizontal
    z = z_base (por padrao a cota de projeto).
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

    # ── Vertices: terreno (0..n-1) + base no plano z=z_base (n..2n-1) ──
    x_all = np.concatenate([x_flat, x_flat])
    y_all = np.concatenate([y_flat, y_flat])
    z_all = np.concatenate([z_flat, np.full_like(z_flat, float(z_base))])

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

    Geometria em elevacao real. Cada regiao e um Mesh3d solido fechado
    entre a superficie do terreno e a plataforma de projeto (z=cota).
    Corte (vermelho) = terreno acima do projeto; aterro (azul) = abaixo.
    """
    fig = go.Figure()
    ox, oy = _offset_xy(superficie)

    # Decima a malha (NumPy) para sólidos leves; volume é calculado à parte
    mx, my, z_terreno = _decimar(
        superficie.malha_x - ox,
        superficie.malha_y - oy,
        superficie.elevacao_malha.astype(float),
    )

    # ── Classificar cada face como corte ou aterro ──
    nrows, ncols = z_terreno.shape
    z_flat = z_terreno.ravel()

    i_all, j_all, k_all = _triangular_grade(nrows, ncols)

    z_cent = (z_flat[i_all] + z_flat[j_all] + z_flat[k_all]) / 3.0
    mascara_corte = z_cent > cota_projeto    # terreno acima -> cortar
    mascara_aterro = z_cent <= cota_projeto  # terreno abaixo -> aterrar

    # ── Solido Aterro (azul): enche do terreno ate a plataforma ──
    trace_aterro = _criar_solido_mesh3d(
        mx, my, z_terreno, CORES["aterro"],
        "Aterro (+)", mascara_aterro, opacidade=0.85, z_base=cota_projeto,
    )
    if trace_aterro is not None:
        fig.add_trace(trace_aterro)

    # ── Solido Corte (vermelho): entre terreno e plataforma de projeto ──
    trace_corte = _criar_solido_mesh3d(
        mx, my, z_terreno, CORES["corte"],
        "Corte (\u2212)", mascara_corte, opacidade=0.85, z_base=cota_projeto,
    )
    if trace_corte is not None:
        fig.add_trace(trace_corte)

    # ── Plataforma de projeto: plano horizontal recortado ao poligono ──
    fig.add_trace(_plano_projeto(mx, my, z_terreno, cota_projeto, opacidade=opacidade_projeto))

    _arrow_norte_3d(fig, mx, my, float(np.nanmin(z_terreno)))

    fig.update_layout(
        title=titulo,
        scene=dict(
            xaxis_title="Leste (m)",
            yaxis_title="Norte (m)",
            zaxis_title="Eleva\u00e7\u00e3o (m)",
            aspectmode="manual",
            aspectratio=_aspecto_cena(mx, my, 1),
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.85)),
        ),
        template=_TEMPLATE,
        height=700,
        margin=dict(l=40, r=20, b=40, t=70),
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
