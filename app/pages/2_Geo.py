"""Geo Analysis page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import plotly.express as px
import streamlit as st

from src import brand, duration, enrich, indian_format, parser

st.set_page_config(page_title="Geo | Airtel CDN Analytics", layout="wide")
st.markdown(brand.STREAMLIT_CSS, unsafe_allow_html=True)

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "Airtel_logs_2.json"


@st.cache_data(show_spinner="Loading…")
def load(mtime: float):
    df = parser.parse_file(DATA_PATH)
    df = enrich.enrich(df)
    df["content_id"] = df["content_id"].fillna("").astype(str).replace("", "Unknown")
    return df


df_raw = load(DATA_PATH.stat().st_mtime)

st.markdown(
    '<div class="hungama-header"><h1>&#9654; Geo Analysis</h1></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<p style="color:#FF6623;font-weight:700;">&#9632; Filters</p>', unsafe_allow_html=True)
    geo_mode = st.radio("View", ["India (IN)", "All Countries"])

df_in = df_raw[df_raw["country"] == "IN"] if geo_mode == "India (IN)" else df_raw

# ── State level ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">State-level Playbacks and Watch (Min)</div>', unsafe_allow_html=True)

state_plays = (
    df_in[df_in["asset_kind"] == "master_manifest"]
    .groupby("state")["session_id"].nunique()
    .reset_index().rename(columns={"session_id": "Playbacks", "state": "State"})
)
state_watch = duration.watch_seconds_by(df_in, "state").reset_index()
state_watch.columns = ["State", "Watch Seconds"]
state_tbl = state_plays.merge(state_watch, on="State", how="outer").fillna(0)
state_tbl["Watch (Min)"] = state_tbl["Watch Seconds"].apply(indian_format.humanize_minutes)
state_tbl["Watch (Hrs)"] = state_tbl["Watch Seconds"].apply(lambda s: indian_format.indian_format(s / 3600))
state_tbl = state_tbl.sort_values("Playbacks", ascending=False)

col_a, col_b = st.columns([3, 2])
with col_a:
    fig_state = px.bar(
        state_tbl.head(15), x="Playbacks", y="State", orientation="h",
        color="Playbacks",
        color_continuous_scale=[[0, brand.SALMON], [1, brand.ORANGE]],
    )
    fig_state.update_layout(**brand.chart_layout("Playbacks by State (Top 15)"))
    fig_state.update_yaxes(autorange="reversed")
    fig_state.update_coloraxes(showscale=False)
    st.plotly_chart(fig_state, use_container_width=True)

with col_b:
    st.dataframe(state_tbl[["State", "Playbacks", "Watch (Min)", "Watch (Hrs)"]], width="stretch", hide_index=True)

# ── City level ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">City Breakdown (sorted by Watch (Min))</div>', unsafe_allow_html=True)

city_plays = (
    df_in[df_in["asset_kind"] == "master_manifest"]
    .groupby(["city", "state"])["session_id"].nunique()
    .reset_index().rename(columns={"session_id": "Playbacks"})
)
city_watch = duration.watch_seconds_by(df_in, "city").reset_index()
city_watch.columns = ["city", "Watch Seconds"]
city_bw = (
    df_in.groupby("city")["object_size"].sum().div(1024 ** 2)
    .reset_index().rename(columns={"object_size": "BW (MB)"})
)
city_tbl = (
    city_plays
    .merge(city_watch, on="city", how="outer")
    .merge(city_bw, on="city", how="outer")
    .fillna(0)
)
city_tbl["Watch (Min)"] = city_tbl["Watch Seconds"].apply(indian_format.humanize_minutes)
city_tbl = city_tbl.rename(columns={"city": "City", "state": "State"}).sort_values("Watch Seconds", ascending=False)
st.dataframe(city_tbl[["City", "State", "Playbacks", "Watch (Min)", "BW (MB)"]], width="stretch", hide_index=True)

fig_city = px.bar(
    city_tbl.head(15), x="Playbacks", y="City", orientation="h",
    color_discrete_sequence=[brand.ORANGE_WARM],
)
fig_city.update_layout(**brand.chart_layout("Top 15 Cities by Playbacks"))
fig_city.update_yaxes(autorange="reversed")
st.plotly_chart(fig_city, use_container_width=True)

# ── Non-IN panel ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">■ Non-IN Traffic (Bot / Probe)</div>', unsafe_allow_html=True)
non_in = df_raw[df_raw["country"] != "IN"]
if not non_in.empty:
    non_in_tbl = (
        non_in.groupby(["country", "city"])
        .agg(Requests=("client_ip", "count"), IPs=("client_ip", "nunique"))
        .sort_values("Requests", ascending=False)
        .reset_index()
        .rename(columns={"country": "Country", "city": "City"})
    )
    st.dataframe(non_in_tbl, width="stretch", hide_index=True)
else:
    st.info("No non-IN traffic in the dataset.")

st.markdown(
    '<div class="hm-footer"><span>Confidential | Hungama Digital Media Entertainment Pvt. Ltd.</span><span>Geo</span></div>',
    unsafe_allow_html=True,
)
