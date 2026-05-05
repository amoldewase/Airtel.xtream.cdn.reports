# Hungama Design System tokens
ORANGE        = "#FF6623"
ORANGE_HOVER  = "#E5591E"
ORANGE_WARM   = "#FF9900"
ORANGE_TINT   = "#FFF3EE"
SALMON        = "#FFE8DC"
GRADIENT      = "linear-gradient(90deg, #FF9900 0%, #FF6623 100%)"
BODY          = "#333333"
CAPTION       = "#6B7280"
BORDER        = "#E5E7EB"
GREEN         = "#22C55E"   # On Track
AMBER         = "#F59E0B"   # At Risk
RED           = "#EF4444"   # Delayed
WHITE         = "#FFFFFF"

_TITLE_FONT = {"color": ORANGE, "size": 16, "family": "Arial, Helvetica, sans-serif"}

PLOTLY_TEMPLATE = {
    "layout": {
        "font": {"family": "Arial, Helvetica, sans-serif", "color": BODY, "size": 13},
        "colorway": [ORANGE, ORANGE_WARM, "#4F3690", "#72BF44", "#09BCEF", "#6B7280"],
        "paper_bgcolor": WHITE,
        "plot_bgcolor": WHITE,
        "xaxis": {"gridcolor": BORDER, "zerolinecolor": BORDER},
        "yaxis": {"gridcolor": BORDER, "zerolinecolor": BORDER},
        "legend": {"font": {"family": "Arial, Helvetica, sans-serif", "color": BODY}},
    },
}


def chart_layout(title: str = None, **extra) -> dict:
    """Return a Plotly layout dict with Hungama brand applied.

    Safe to use with an explicit title:
        fig.update_layout(**brand.chart_layout("My Chart"))
    """
    base = dict(PLOTLY_TEMPLATE["layout"])
    base["title"] = {"text": title or "", "font": _TITLE_FONT}
    base.update(extra)
    return base

STREAMLIT_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Arial');

    html, body, [class*="css"] {{
        font-family: Arial, Helvetica, sans-serif !important;
        color: {BODY};
    }}

    /* Header band */
    .hungama-header {{
        background: {GRADIENT};
        padding: 12px 24px;
        border-radius: 4px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    .hungama-header h1 {{
        color: {WHITE};
        font-family: Arial, Helvetica, sans-serif;
        font-size: 22px;
        font-weight: 700;
        margin: 0;
    }}
    .hungama-header .refresh-ts {{
        color: rgba(255,255,255,0.85);
        font-size: 12px;
    }}

    /* KPI tiles */
    .kpi-tile {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 20px 18px 16px 18px;
        border-top: 4px solid {ORANGE};
        min-height: 120px;
    }}
    .kpi-tile .kpi-label {{
        font-size: 11px;
        color: {CAPTION};
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 8px;
        font-weight: 600;
    }}
    .kpi-tile .kpi-value {{
        font-size: 34px;
        font-weight: 700;
        color: {ORANGE};
        font-family: Arial, Helvetica, sans-serif;
        line-height: 1.1;
        letter-spacing: -0.5px;
    }}
    .kpi-tile .kpi-secondary {{
        font-size: 12px;
        color: {CAPTION};
        margin-top: 6px;
        border-top: 1px solid {BORDER};
        padding-top: 6px;
    }}

    /* Section titles */
    .section-title {{
        color: {ORANGE};
        font-family: Arial, Helvetica, sans-serif;
        font-size: 15px;
        font-weight: 700;
        border-bottom: 2px solid {ORANGE};
        padding-bottom: 4px;
        margin-bottom: 12px;
    }}

    /* Orange rule */
    .orange-rule {{
        border: none;
        border-top: 2px solid {ORANGE};
        margin: 16px 0;
    }}

    /* Bullet list */
    .hm-bullet {{
        color: {ORANGE};
        font-weight: bold;
    }}

    /* Footer */
    .hm-footer {{
        border-top: 2px solid {ORANGE};
        padding-top: 8px;
        margin-top: 24px;
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: {CAPTION};
    }}

    /* Tab active highlight */
    [data-baseweb="tab"][aria-selected="true"] {{
        border-bottom-color: {ORANGE} !important;
        color: {ORANGE} !important;
    }}

    /* Metric delta positive */
    [data-testid="stMetricDelta"] {{
        color: {GREEN};
    }}

    /* Streamlit default button */
    .stButton > button {{
        background-color: {ORANGE};
        color: {WHITE};
        border: none;
        border-radius: 4px;
        font-family: Arial, Helvetica, sans-serif;
    }}
    .stButton > button:hover {{
        background-color: {ORANGE_HOVER};
    }}

    /* Remove default streamlit blue accents */
    .stSelectbox [data-baseweb="select"] {{
        border-color: {BORDER};
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {ORANGE_TINT};
    }}
    [data-testid="stSidebar"] .sidebar-title {{
        color: {ORANGE};
        font-weight: 700;
    }}
</style>
"""
