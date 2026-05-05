"""Content Analysis page — table + per-content drill-down dashboard."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import plotly.express as px
import streamlit as st

from src import brand, duration, enrich, indian_format, parser

st.set_page_config(page_title="Content | Airtel CDN Analytics", layout="wide")
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
    '<div class="hungama-header"><h1>&#9654; Content Analysis</h1></div>',
    unsafe_allow_html=True,
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="color:#FF6623;font-weight:700;">&#9632; Filters</p>', unsafe_allow_html=True)
    countries = sorted(df_raw["country"].dropna().unique())
    sel_country = st.multiselect("Country", countries, default=["IN"])

df = df_raw[df_raw["country"].isin(sel_country)] if sel_country else df_raw
df = df[df["content_id"] != "Unknown"].copy()

# ── Build summary table ────────────────────────────────────────────────────────
plays = (
    df[(df["asset_kind"] == "master_manifest") & (df["http_status"] == 200)]
    .groupby("content_id")["session_id"].nunique().reset_index()
    .rename(columns={"session_id": "Playbacks", "content_id": "Content ID"})
)
watch = duration.watch_seconds_by(df, "content_id").reset_index()
watch.columns = ["Content ID", "Watch Seconds"]
bw = (
    df.groupby("content_id")["object_size"].sum().div(1024**2).reset_index()
    .rename(columns={"object_size": "BW (MB)", "content_id": "Content ID"})
)
unique_sess = (
    df.groupby("content_id")["session_id"].nunique().reset_index()
    .rename(columns={"session_id": "Unique Sessions", "content_id": "Content ID"})
)
unique_ips = (
    df.groupby("content_id")["client_ip"].nunique().reset_index()
    .rename(columns={"client_ip": "Unique IPs", "content_id": "Content ID"})
)

tbl = (
    plays.merge(watch, on="Content ID", how="outer")
    .merge(bw, on="Content ID", how="outer")
    .merge(unique_sess, on="Content ID", how="outer")
    .merge(unique_ips, on="Content ID", how="outer")
    .fillna(0)
)
tbl["Content ID"]   = tbl["Content ID"].astype(str)
tbl["Watch (Min)"]  = tbl["Watch Seconds"].apply(indian_format.humanize_minutes)
tbl["Bandwidth"]    = tbl["BW (MB)"].apply(lambda b: f"{b:.2f} MB")
tbl = tbl.sort_values("Playbacks", ascending=False)

# ── Summary charts ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Content Performance Overview</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(tbl.head(10), x="Playbacks", y="Content ID", orientation="h",
                 color_discrete_sequence=[brand.ORANGE])
    fig.update_layout(**brand.chart_layout("Top 10 by Playbacks"))
    fig.update_yaxes(autorange="reversed", type="category")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig2 = px.bar(tbl.sort_values("Watch Seconds", ascending=False).head(10),
                  x="Watch Seconds", y="Content ID", orientation="h",
                  color_discrete_sequence=[brand.ORANGE_WARM])
    fig2.update_layout(**brand.chart_layout("Top 10 by Watch Time"))
    fig2.update_yaxes(autorange="reversed", type="category")
    st.plotly_chart(fig2, use_container_width=True)

# ── Summary table with drill-down trigger ──────────────────────────────────────
st.markdown('<div class="section-title">All Content IDs — click a row then select below to drill in</div>', unsafe_allow_html=True)
st.dataframe(
    tbl[["Content ID", "Playbacks", "Unique Sessions", "Unique IPs", "Watch (Min)", "Bandwidth"]],
    width="stretch", hide_index=True,
)

csv = tbl.to_csv(index=False).encode("utf-8")
st.download_button("Download Content Report (CSV)", csv, "content_report.csv", "text/csv")

st.markdown('<hr class="orange-rule">', unsafe_allow_html=True)

# ── Content ID drill-down ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">&#9660; Content ID Deep Dive</div>', unsafe_allow_html=True)

# Honour ?content_id= query param (set by clicking a content ID link)
qp_cid = st.query_params.get("content_id", None)
content_ids_available = tbl["Content ID"].tolist()

selected_cid = st.selectbox(
    "Select Content ID to analyse",
    options=["— select —"] + content_ids_available,
    index=(content_ids_available.index(qp_cid) + 1) if qp_cid in content_ids_available else 0,
)

if selected_cid != "— select —":
    # Update query param so URL is bookmarkable
    st.query_params["content_id"] = selected_cid

    dfd = df[df["content_id"] == selected_cid].copy()

    # ── KPI tiles for this content ─────────────────────────────────────────────
    c_plays = int(
        dfd[(dfd["asset_kind"] == "master_manifest") & (dfd["http_status"] == 200)]
        ["session_id"].nunique()
    )
    c_sessions  = int(dfd["session_id"].nunique())
    c_ips       = int(dfd["client_ip"].nunique())
    c_secs      = duration.total_watch_seconds(dfd)
    c_bw        = dfd["object_size"].fillna(0).sum()
    c_errors    = int((dfd["http_status"] >= 400).sum())
    c_cache_pct = (dfd["cache_status"] == 1).sum() / max(len(dfd), 1) * 100

    def _tile(label, value, sub=""):
        return f"""<div class="kpi-tile">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-secondary">{sub}</div>
        </div>"""

    st.markdown(f"### Content ID: `{selected_cid}`")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(_tile("Playbacks",      str(c_plays),                           "master manifest 200 OK"), unsafe_allow_html=True)
    k2.markdown(_tile("Unique Sessions", str(c_sessions),                       "all asset types"), unsafe_allow_html=True)
    k3.markdown(_tile("Unique IPs",     str(c_ips),                             ""), unsafe_allow_html=True)
    k4.markdown(_tile("Watch (Min)",    indian_format.humanize_minutes(c_secs), indian_format.humanize_seconds(c_secs)), unsafe_allow_html=True)
    k5.markdown(_tile("Bandwidth",      indian_format.humanize_bytes(c_bw),     "total delivered"), unsafe_allow_html=True)
    k6.markdown(_tile("Cache Hit %",    f"{c_cache_pct:.1f}%",                  f"{c_errors} errors"), unsafe_allow_html=True)

    st.markdown('<hr class="orange-rule">', unsafe_allow_html=True)

    # ── Time series ────────────────────────────────────────────────────────────
    col_ts1, col_ts2 = st.columns(2)
    with col_ts1:
        st.markdown("**Playbacks over time**")
        df_ts = dfd[(dfd["asset_kind"] == "master_manifest") & (dfd["http_status"] == 200)].copy()
        if not df_ts.empty:
            df_ts["hour"] = df_ts["request_ts_ist"].dt.floor("h")
            fig_ts = px.area(
                df_ts.groupby("hour")["session_id"].nunique().reset_index()
                .rename(columns={"session_id": "Playbacks", "hour": "Hour (IST)"}),
                x="Hour (IST)", y="Playbacks",
                color_discrete_sequence=[brand.ORANGE],
            )
            fig_ts.update_traces(line_color=brand.ORANGE, fillcolor=brand.SALMON)
            fig_ts.update_layout(**brand.chart_layout("Playbacks per Hour"))
            st.plotly_chart(fig_ts, use_container_width=True)

    with col_ts2:
        st.markdown("**Bandwidth over time (MB)**")
        dfd_bw = dfd.copy()
        dfd_bw["hour"] = dfd_bw["request_ts_ist"].dt.floor("h")
        fig_bwt = px.bar(
            dfd_bw.groupby("hour")["object_size"].sum().div(1024**2).reset_index()
            .rename(columns={"object_size": "MB", "hour": "Hour (IST)"}),
            x="Hour (IST)", y="MB",
            color_discrete_sequence=[brand.ORANGE_WARM],
        )
        fig_bwt.update_layout(**brand.chart_layout("Bandwidth per Hour"))
        st.plotly_chart(fig_bwt, use_container_width=True)

    # ── Session breakdown ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Sessions for this Content ID</div>', unsafe_allow_html=True)
    sess_w = duration.watch_seconds_by_session(dfd)
    sess_d = (
        dfd.groupby("session_id")
        .agg(
            client_ip=("client_ip", "first"),
            city=("city", "first"),
            state=("state", "first"),
            requests=("request_path", "count"),
            errors=("http_status", lambda x: int((x >= 400).sum())),
        ).reset_index()
    )
    sess_d = sess_d.merge(sess_w[["session_id", "watch_seconds", "segment_count"]], on="session_id", how="left")
    sess_d["watch_seconds"]  = sess_d["watch_seconds"].fillna(0)
    sess_d["segment_count"]  = sess_d["segment_count"].fillna(0).astype(int)
    sess_d["Watch (Min)"]    = sess_d["watch_seconds"].apply(indian_format.humanize_minutes)

    def _label(sid):
        return f"Anonymous ({sid.split('::')[1]})" if sid.startswith("anon::") else sid

    sess_d["Session"] = sess_d["session_id"].apply(_label)

    st.dataframe(
        sess_d[["Session", "client_ip", "city", "state", "Watch (Min)", "segment_count", "requests", "errors"]]
        .rename(columns={
            "client_ip": "Client IP", "city": "City", "state": "State",
            "segment_count": "Segments", "requests": "Requests", "errors": "Errors",
        }),
        width="stretch", hide_index=True,
    )

    # ── Asset kind breakdown ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">Asset Mix for this Content ID</div>', unsafe_allow_html=True)
    asset_counts = dfd["asset_kind"].value_counts().reset_index()
    asset_counts.columns = ["Asset Kind", "Count"]
    fig_asset = px.bar(asset_counts, x="Asset Kind", y="Count",
                       color_discrete_sequence=[brand.ORANGE])
    fig_asset.update_layout(**brand.chart_layout("Asset Kind Distribution"))
    st.plotly_chart(fig_asset, use_container_width=True)

    # ── IP breakdown ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">IP Breakdown</div>', unsafe_allow_html=True)
    ip_tbl = (
        dfd.groupby(["client_ip", "city", "state", "country"])
        .agg(Requests=("request_path", "count"), Errors=("http_status", lambda x: int((x >= 400).sum())))
        .reset_index()
        .rename(columns={"client_ip": "Client IP", "city": "City", "state": "State", "country": "Country"})
        .sort_values("Requests", ascending=False)
    )
    st.dataframe(ip_tbl, width="stretch", hide_index=True)

else:
    st.info("Select a Content ID above to open its full detail dashboard.")

st.markdown(
    '<div class="hm-footer"><span>Confidential | Hungama Digital Media Entertainment Pvt. Ltd.</span>'
    '<span>Content Analysis</span></div>',
    unsafe_allow_html=True,
)
