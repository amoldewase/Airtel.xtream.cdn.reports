"""Bandwidth and Performance page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import brand, enrich, indian_format, parser

st.set_page_config(page_title="Bandwidth | Airtel CDN Analytics", layout="wide")
st.markdown(brand.STREAMLIT_CSS, unsafe_allow_html=True)

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "Airtel_logs_2.json"


@st.cache_data(show_spinner="Loading…")
def load(mtime: float):
    df = parser.parse_file(DATA_PATH)
    return enrich.enrich(df)


df_raw = load(DATA_PATH.stat().st_mtime)

st.markdown(
    '<div class="hungama-header"><h1>&#9654; Bandwidth &amp; Performance</h1></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<p style="color:#FF6623;font-weight:700;">&#9632; Filters</p>', unsafe_allow_html=True)
    countries = sorted(df_raw["country"].dropna().unique())
    sel_country = st.multiselect("Country", countries, default=["IN"])

df = df_raw[df_raw["country"].isin(sel_country)] if sel_country else df_raw

total_bw = df["object_size"].fillna(0).sum()
avg_obj = df["object_size"].mean()
p95_obj = df["object_size"].quantile(0.95)

c1, c2, c3 = st.columns(3)
c1.metric("Total Bandwidth", indian_format.humanize_bytes(total_bw))
c2.metric("Avg Object Size", indian_format.humanize_bytes(avg_obj or 0))
c3.metric("p95 Object Size", indian_format.humanize_bytes(p95_obj or 0))

st.markdown('<hr class="orange-rule">', unsafe_allow_html=True)

# ── Histogram ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Object Size Distribution</div>', unsafe_allow_html=True)
df_pos = df[df["object_size"].notna() & (df["object_size"] > 0)]
fig_hist = px.histogram(
    df_pos, x="object_size", nbins=60,
    labels={"object_size": "Object Size (bytes)"},
    color_discrete_sequence=[brand.ORANGE],
)
fig_hist.update_layout(**brand.chart_layout("Object Size Histogram"))
st.plotly_chart(fig_hist, use_container_width=True)

# ── Bandwidth over time ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Bandwidth per Hour (MB)</div>', unsafe_allow_html=True)
df_t = df.copy()
df_t["hour"] = df_t["request_ts_ist"].dt.floor("h")
hourly_bw = (
    df_t.groupby("hour")["object_size"].sum().div(1024 ** 2)
    .reset_index().rename(columns={"object_size": "MB", "hour": "Hour (IST)"})
)
fig_bw = px.area(
    hourly_bw, x="Hour (IST)", y="MB",
    color_discrete_sequence=[brand.ORANGE_WARM],
)
fig_bw.update_layout(**brand.chart_layout("Bandwidth per Hour"))
fig_bw.update_traces(fillcolor=brand.SALMON)
st.plotly_chart(fig_bw, use_container_width=True)

# ── Latency p50 / p95 ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Edge Latency p50 / p95 (ms)</div>', unsafe_allow_html=True)
df_lat = df[df["turn_around_ms"].notna() & (df["turn_around_ms"] >= 1)].copy()
if not df_lat.empty:
    df_lat["hour"] = df_lat["request_ts_ist"].dt.floor("h")
    lat = (
        df_lat.groupby("hour")["turn_around_ms"]
        .agg(p50=lambda x: x.quantile(0.5), p95=lambda x: x.quantile(0.95))
        .reset_index()
    )
    fig_lat = go.Figure()
    fig_lat.add_trace(go.Scatter(x=lat["hour"], y=lat["p50"], name="p50 ms", line=dict(color=brand.ORANGE)))
    fig_lat.add_trace(go.Scatter(x=lat["hour"], y=lat["p95"], name="p95 ms", line=dict(color=brand.AMBER, dash="dash")))
    fig_lat.update_layout(
        **brand.chart_layout(
            "Edge Latency per Hour",
            xaxis_title="Hour (IST)",
            yaxis_title="Turn-around time (ms)",
        )
    )
    st.plotly_chart(fig_lat, use_container_width=True)

    m1, m2 = st.columns(2)
    m1.metric("Overall p50 Latency (ms)", f"{df_lat['turn_around_ms'].quantile(0.5):.0f}")
    m2.metric("Overall p95 Latency (ms)", f"{df_lat['turn_around_ms'].quantile(0.95):.0f}")

# ── Cache hit ratio ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Cache Hit Ratio Over Time</div>', unsafe_allow_html=True)
df_c = df[df["cache_status"].notna()].copy()
if not df_c.empty:
    df_c["hour"] = df_c["request_ts_ist"].dt.floor("h")
    cache_h = (
        df_c.groupby("hour")
        .apply(lambda x: (x["cache_status"] == 1).sum() / len(x) * 100, include_groups=False)
        .reset_index()
        .rename(columns={0: "Cache Hit %", "hour": "Hour (IST)"})
    )
    fig_cache = px.line(cache_h, x="Hour (IST)", y="Cache Hit %", color_discrete_sequence=[brand.GREEN])
    fig_cache.update_layout(**brand.chart_layout("Cache Hit % per Hour"))
    fig_cache.add_hline(y=50, line_dash="dot", line_color=brand.AMBER, annotation_text="50% threshold")
    st.plotly_chart(fig_cache, use_container_width=True)

# ── Throughput summary ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Per-Row Throughput (Mbps)</div>', unsafe_allow_html=True)
df_mbps = df[df["mbps"].notna()]
if not df_mbps.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Avg Mbps", f"{df_mbps['mbps'].mean():.3f}")
    m2.metric("p95 Mbps", f"{df_mbps['mbps'].quantile(0.95):.3f}")
    m3.metric("Max Mbps", f"{df_mbps['mbps'].max():.3f}")

st.markdown(
    '<div class="hm-footer"><span>Confidential | Hungama Digital Media Entertainment Pvt. Ltd.</span><span>Bandwidth</span></div>',
    unsafe_allow_html=True,
)
