"""Tema minimalista compartilhado para toda a aplicacao Streamlit."""

import streamlit as st

# ── Cores do tema ──
CORES = {
    "bg": "#fafafa",
    "bg_secondary": "#f4f4f5",
    "text": "#27272a",
    "text_secondary": "#3f3f46",
    "text_muted": "#71717a",
    "text_label": "#52525b",
    "accent": "#6366f1",
    "accent_light": "rgba(99,102,241,0.1)",
    "border": "#e4e4e7",
    "border_light": "#f4f4f5",
    "success": "#10b981",
    "danger": "#ef4444",
    "warning": "#d97706",
    "white": "#ffffff",
    # plotly
    "corte": "#e11d48",
    "aterro": "#6366f1",
    "bota_fora": "#d97706",
    "solo_imp": "#10b981",
}

# ── Layout Plotly minimalista ──
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", size=12, color="#3f3f46"),
    margin=dict(l=48, r=24, t=40, b=40),
    title=dict(font=dict(size=14, color="#27272a"), x=0, xanchor="left"),
    legend=dict(
        font=dict(size=11),
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
    ),
    xaxis=dict(
        gridcolor="#f4f4f5",
        zerolinecolor="#e4e4e7",
        linecolor="#e4e4e7",
        title_font=dict(size=11, color="#71717a"),
        tickfont=dict(size=10, color="#71717a"),
    ),
    yaxis=dict(
        gridcolor="#f4f4f5",
        zerolinecolor="#e4e4e7",
        linecolor="#e4e4e7",
        title_font=dict(size=11, color="#71717a"),
        tickfont=dict(size=10, color="#71717a"),
    ),
)

PLOTLY_SCENE = dict(
    xaxis=dict(
        backgroundcolor="rgba(0,0,0,0)",
        gridcolor="#e4e4e7",
        title_font=dict(size=10, color="#71717a"),
        tickfont=dict(size=9, color="#71717a"),
    ),
    yaxis=dict(
        backgroundcolor="rgba(0,0,0,0)",
        gridcolor="#e4e4e7",
        title_font=dict(size=10, color="#71717a"),
        tickfont=dict(size=9, color="#71717a"),
    ),
    zaxis=dict(
        backgroundcolor="rgba(0,0,0,0)",
        gridcolor="#e4e4e7",
        title_font=dict(size=10, color="#71717a"),
        tickfont=dict(size=9, color="#71717a"),
    ),
)


def aplicar_tema():
    """Injeta CSS minimalista global. Chamar uma vez no app.py."""
    st.html("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

        /* ── Ocultar chrome do Streamlit ── */
        #MainMenu, footer, header,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stDeployButton { display: none !important; }

        /* ── Tipografia global ── */
        html, body, [class*="st-"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }

        .main .block-container {
            padding: 2rem 3rem 2rem 3rem;
            max-width: 1100px;
        }

        /* ── Headings: menores, mais leves ── */
        h1 {
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.025em !important;
            color: #18181b !important;
        }
        h2 {
            font-size: 1.15rem !important;
            font-weight: 500 !important;
            letter-spacing: -0.01em !important;
            color: #27272a !important;
        }
        h3 {
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            color: #3f3f46 !important;
        }

        /* ── Texto body: menor ── */
        p, li, span, label, .stMarkdown {
            font-size: 0.875rem !important;
            color: #3f3f46 !important;
            line-height: 1.6 !important;
        }

        /* ── Labels dos inputs ── */
        .stSelectbox label, .stTextInput label, .stNumberInput label,
        .stSlider label, .stDateInput label, .stTextArea label,
        .stFileUploader label, .stCheckbox label, .stRadio label {
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            color: #52525b !important;
            letter-spacing: 0.01em !important;
        }

        /* ── Espacamento vertical reduzido ── */
        [data-testid="stVerticalBlock"] > div {
            gap: 0.4rem !important;
        }

        /* ── Inputs: sutis, arredondados ── */
        .stTextInput input, .stNumberInput input, .stDateInput input {
            border: 1px solid #d4d4d8 !important;
            border-radius: 8px !important;
            padding: 0.5rem 0.75rem !important;
            font-size: 0.85rem !important;
            background: #fafafa !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 2px rgba(99,102,241,0.1) !important;
        }

        .stSelectbox > div > div {
            border-radius: 8px !important;
            font-size: 0.85rem !important;
        }

        /* ── Botoes: limpos ── */
        .stButton > button {
            border-radius: 8px !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            padding: 0.45rem 1.2rem !important;
            border: 1px solid #d4d4d8 !important;
            background: #ffffff !important;
            color: #18181b !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
            transition: all 0.15s ease !important;
        }
        .stButton > button:hover {
            background: #f4f4f5 !important;
            border-color: #a1a1aa !important;
        }

        /* ── Download buttons ── */
        .stDownloadButton > button {
            border-radius: 8px !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 1.2rem !important;
            background: #18181b !important;
            color: #ffffff !important;
            border: none !important;
            transition: all 0.15s ease !important;
        }
        .stDownloadButton > button:hover {
            background: #27272a !important;
        }

        /* ── Sidebar: limpa ── */
        [data-testid="stSidebar"] {
            background-color: #fafafa !important;
            border-right: 1px solid #e4e4e7 !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
            color: #71717a !important;
        }

        /* ── Metrics: mais sutis ── */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e4e4e7;
            border-radius: 10px;
            padding: 0.8rem 1rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
            color: #71717a !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            color: #18181b !important;
        }

        /* ── Expander: limpo ── */
        .streamlit-expanderHeader {
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            color: #27272a !important;
            background: #ffffff !important;
            border: 1px solid #e4e4e7 !important;
            border-radius: 8px !important;
        }

        /* ── Divider: sutil ── */
        hr {
            border: none !important;
            border-top: 1px solid #f4f4f5 !important;
            margin: 1rem 0 !important;
        }

        /* ── Tabs: underline style ── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0 !important;
            border-bottom: 1px solid #e4e4e7 !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
            color: #71717a !important;
        }
        .stTabs [aria-selected="true"] {
            color: #18181b !important;
        }

        /* ── Dataframes ── */
        [data-testid="stDataFrame"] {
            border: 1px solid #e4e4e7 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }

        /* ── Info/Warning/Success boxes ── */
        .stAlert {
            border-radius: 8px !important;
            font-size: 0.8rem !important;
        }

        /* ── Caption ── */
        .stCaption, [data-testid="stCaptionContainer"] {
            font-size: 0.75rem !important;
            color: #a1a1aa !important;
        }
    </style>
    """)


def section_header(texto: str):
    """Header de secao minimalista (uppercase micro-label)."""
    st.html(
        '<div style="font-size:0.7rem;font-weight:600;text-transform:uppercase;'
        'letter-spacing:0.06em;color:#a1a1aa;margin-top:1.5rem;margin-bottom:0.5rem;'
        'padding-bottom:0.4rem;border-bottom:1px solid #f4f4f5;">{}</div>'.format(texto),
    )
