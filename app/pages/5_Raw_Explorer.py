"""Raw Explorer page - paginated parsed-row table with CSV export."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from src import brand, enrich, parser

st.set_page_config(page_title="Raw Explorer | Airtel CDN Analytics", layout="wide")
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
    '<div class="hungama-header"><h1>&#9654; Raw Data Explorer</h1></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<p style="color:#FF6623;font-weight:700;">&#9632; Filters</p>', unsafe_allow_html=True)
    countries = sorted(df_raw["country"].dropna().unique())
    sel_country = st.multiselect("Country", countries, default=["IN"])
    asset_opts = ["All"] + sorted(df_raw["asset_kind"].dropna().unique().tolist())
    sel_asset = st.selectbox("Asset Kind", asset_opts)
    status_opts = sorted(df_raw["http_status"].dropna().unique().tolist())
    sel_status = st.multiselect("HTTP Status", status_opts, default=[200])

df = df_raw[df_raw["country"].isin(sel_country)] if sel_country else df_raw
if sel_asset != "All":
    df = df[df["asset_kind"] == sel_asset]
if sel_status:
    df = df[df["http_status"].isin(sel_status)]

all_cols = df.columns.tolist()
default_cols = [c for c in [
    "request_ts_ist", "session_id", "client_ip", "country", "city", "state",
    "http_status", "asset_kind", "content_id", "segment_no",
    "object_size", "cache_status", "turn_around_ms", "playback_seconds", "mbps",
] if c in all_cols]

sel_cols = st.multiselect("Columns to display", all_cols, default=default_cols)

page_size = st.select_slider("Rows per page", [25, 50, 100, 250, 500], value=100)
total_pages = max(1, (len(df) + page_size - 1) // page_size)
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

start = (page - 1) * page_size
end = start + page_size
df_page = df[sel_cols].iloc[start:end] if sel_cols else df.iloc[start:end]

st.markdown(
    f'<div class="section-title">Rows {start+1}–{min(end, len(df))} of {len(df):,} (Page {page}/{total_pages})</div>',
    unsafe_allow_html=True,
)
st.dataframe(df_page, width="stretch", hide_index=True)

csv = (df[sel_cols] if sel_cols else df).to_csv(index=False).encode("utf-8")
st.download_button("Download Full Filtered CSV", csv, "airtel_cdn_raw.csv", "text/csv")

st.markdown(
    '<div class="hm-footer"><span>Confidential | Hungama Digital Media Entertainment Pvt. Ltd.</span><span>Raw Explorer</span></div>',
    unsafe_allow_html=True,
)
