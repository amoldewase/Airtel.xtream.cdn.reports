"""Airtel CDN Analytics Dashboard - Main Entry Point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import brand, duration, enrich, indian_format, parser

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Airtel CDN Analytics | Hungama",
    page_icon="▶",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(brand.STREAMLIT_CSS, unsafe_allow_html=True)

DATA_PATH = Path(__file__).parent.parent / "data" / "Airtel_logs_2.json"
PARQUET_PATH = Path(__file__).parent.parent / "data" / "parsed.parquet"


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Parsing log file…")
def load_data(mtime: float) -> pd.DataFrame:
    df = parser.parse_file(DATA_PATH)
    df = enrich.enrich(df)
    df["content_id"] = df["content_id"].fillna("").astype(str).replace("", "Unknown")
    parser.save_parquet(df, PARQUET_PATH)
    return df


mtime = DATA_PATH.stat().st_mtime if DATA_PATH.exists() else 0.0
df_raw = load_data(mtime)

# ── Header ─────────────────────────────────────────────────────────────────────
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
refresh_str = datetime.now(IST).strftime("%d/%m/%Y %H:%M:%S IST")

st.markdown(
    f"""<div class="hungama-header">
        <h1>&#9654; Airtel CDN Analytics</h1>
        <span class="refresh-ts">Last refreshed: {refresh_str}</span>
    </div>""",
    unsafe_allow_html=True,
)

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="color:#FF6623;font-weight:700;font-size:15px;">&#9632; Filters</p>', unsafe_allow_html=True)

    all_countries = sorted(df_raw["country"].dropna().unique())
    sel_country = st.multiselect("Country", all_countries, default=["IN"])

    all_states = sorted(df_raw["state"].dropna().unique())
    sel_state = st.multiselect("State", all_states, default=[])

    all_cities = [c for c in sorted(df_raw["city"].dropna().unique()) if c != "Unknown"]
    sel_city = st.multiselect("City", all_cities, default=[])

    all_contents = [c for c in sorted(df_raw["content_id"].dropna().unique()) if c not in ("", "Unknown")]
    sel_content = st.multiselect("Content ID", all_contents, default=[])

    status_opts = sorted(df_raw["http_status"].dropna().unique().tolist())
    sel_status = st.multiselect("HTTP Status", status_opts, default=[200])

    cache_opts = ["All", "Cache Hit", "Cache Miss"]
    sel_cache = st.selectbox("Cache Status", cache_opts, index=0)

    asset_opts = ["All"] + sorted(df_raw["asset_kind"].dropna().unique().tolist())
    sel_asset = st.selectbox("Asset Kind", asset_opts, index=0)

    st.markdown("---")
    st.caption("■ Hungama Digital Media Entertainment Pvt. Ltd.")


# ── Apply filters ──────────────────────────────────────────────────────────────
def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if sel_country:
        df = df[df["country"].isin(sel_country)]
    if sel_state:
        df = df[df["state"].isin(sel_state)]
    if sel_city:
        df = df[df["city"].isin(sel_city)]
    if sel_content:
        df = df[df["content_id"].isin(sel_content)]
    if sel_status:
        df = df[df["http_status"].isin(sel_status)]
    if sel_cache == "Cache Hit":
        df = df[df["cache_status"] == 1]
    elif sel_cache == "Cache Miss":
        df = df[df["cache_status"] == 0]
    if sel_asset != "All":
        df = df[df["asset_kind"] == sel_asset]
    return df


df = apply_filters(df_raw)

# ── KPI computations ───────────────────────────────────────────────────────────
df_in = df[df["country"] == "IN"]
df_plays = df_in[(df_in["asset_kind"] == "master_manifest") & (df_in["http_status"] == 200)]

total_playbacks   = df_plays["session_id"].nunique()
unique_sessions   = df["session_id"].nunique()
unique_ips_in     = df_in["client_ip"].nunique()
unique_ips_non_in = df[df["country"] != "IN"]["client_ip"].nunique()
total_secs        = duration.total_watch_seconds(df)
total_bytes       = df["object_size"].fillna(0).sum()
total_rows        = len(df)
cache_hits        = int((df["cache_status"] == 1).sum())
cache_hit_pct     = (cache_hits / total_rows * 100) if total_rows > 0 else 0.0
anon_count        = df[df["session_id"].str.startswith("anon::")]["session_id"].nunique()
anon_pct          = anon_count / max(unique_sessions, 1) * 100


# ── KPI tile helper ────────────────────────────────────────────────────────────
def kpi_tile(label: str, value: str, secondary: str = "") -> str:
    return f"""<div class="kpi-tile">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-secondary">{secondary}</div>
    </div>"""


# ── KPI row ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Key Performance Indicators</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.markdown(kpi_tile(
        "Total Playbacks (IN)",
        indian_format.indian_format(total_playbacks),
        "Successful starts (200 OK)"
    ), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_tile(
        "Unique Sessions",
        indian_format.indian_format(unique_sessions),
        f"{anon_pct:.1f}% anonymous fallback"
    ), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_tile(
        "Unique IPs (IN)",
        indian_format._indian_comma(unique_ips_in),
        f"+{unique_ips_non_in} non-IN (bot/probe)"
    ), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_tile(
        "Total Watch Time",
        indian_format.humanize_minutes(total_secs),
        indian_format.humanize_seconds(total_secs)
    ), unsafe_allow_html=True)
with c5:
    st.markdown(kpi_tile(
        "Total Bandwidth",
        indian_format.humanize_bytes(total_bytes),
        "sum of object_size delivered"
    ), unsafe_allow_html=True)
with c6:
    st.markdown(kpi_tile(
        "Cache Hit %",
        f"{cache_hit_pct:.1f}%",
        f"{cache_hits:,} hits / {total_rows:,} requests"
    ), unsafe_allow_html=True)

st.markdown('<hr class="orange-rule">', unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_overview, tab_content, tab_geo, tab_sessions, tab_bw, tab_raw = st.tabs([
    "Overview", "Content", "Geo", "Sessions", "Bandwidth & Perf", "Raw Explorer"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ════════════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.markdown('<div class="section-title">Playbacks per Hour (IST)</div>', unsafe_allow_html=True)

    if not df_plays.empty:
        df_pb = df_plays.copy()
        df_pb["hour"] = df_pb["request_ts_ist"].dt.floor("h")
        hourly_plays = (
            df_pb.groupby("hour")["session_id"].nunique().reset_index()
            .rename(columns={"session_id": "Playbacks", "hour": "Hour (IST)"})
        )
        fig_pb = px.area(hourly_plays, x="Hour (IST)", y="Playbacks",
                         color_discrete_sequence=[brand.ORANGE])
        fig_pb.update_traces(line_color=brand.ORANGE, fillcolor=brand.SALMON)
        fig_pb.update_layout(**brand.chart_layout("Playbacks per Hour"))
        st.plotly_chart(fig_pb, use_container_width=True)
    else:
        st.info("No playback data for current filters.")

    col_bw, col_err = st.columns([2, 1])

    with col_bw:
        st.markdown('<div class="section-title">Bandwidth per Hour (MB)</div>', unsafe_allow_html=True)
        if df["object_size"].notna().any():
            df_bt = df.copy()
            df_bt["hour"] = df_bt["request_ts_ist"].dt.floor("h")
            hourly_bw = (
                df_bt.groupby("hour")["object_size"].sum().div(1024**2).reset_index()
                .rename(columns={"object_size": "MB", "hour": "Hour (IST)"})
            )
            fig_bw = px.bar(hourly_bw, x="Hour (IST)", y="MB",
                            color_discrete_sequence=[brand.ORANGE_WARM])
            fig_bw.update_layout(**brand.chart_layout("Bandwidth per Hour"))
            st.plotly_chart(fig_bw, use_container_width=True)
        else:
            st.info("No bandwidth data.")

    with col_err:
        st.markdown('<div class="section-title">HTTP Status Mix</div>', unsafe_allow_html=True)
        sc = df["http_status"].value_counts().reset_index()
        sc.columns = ["Status", "Count"]
        sc["Status"] = sc["Status"].astype(str)
        colors = [{"200": brand.GREEN, "403": brand.AMBER, "404": brand.RED}.get(s, brand.CAPTION) for s in sc["Status"]]
        fig_donut = go.Figure(go.Pie(
            labels=sc["Status"], values=sc["Count"], hole=0.55,
            marker_colors=colors,
            textfont=dict(family="Arial, Helvetica, sans-serif"),
        ))
        fig_donut.update_layout(**brand.chart_layout("HTTP Status Mix"),
                                showlegend=True, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown('<div class="section-title">■ Non-IN Traffic (Bot / Probe)</div>', unsafe_allow_html=True)
    df_non_in = df_raw[df_raw["country"] != "IN"]
    if not df_non_in.empty:
        non_in_summary = (
            df_non_in.groupby("country")
            .agg(Requests=("client_ip", "count"), Unique_IPs=("client_ip", "nunique"))
            .sort_values("Requests", ascending=False).reset_index()
            .rename(columns={"country": "Country", "Unique_IPs": "Unique IPs"})
        )
        st.dataframe(non_in_summary, width="stretch", hide_index=True)
    else:
        st.info("No non-IN traffic.")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 – CONTENT
# ════════════════════════════════════════════════════════════════════════════════
with tab_content:
    st.markdown('<div class="section-title">Top 20 Content IDs</div>', unsafe_allow_html=True)

    dfc = df[df["content_id"] != "Unknown"].copy()

    content_plays = (
        dfc[(dfc["asset_kind"] == "master_manifest") & (dfc["http_status"] == 200)]
        .groupby("content_id")["session_id"].nunique().reset_index()
        .rename(columns={"session_id": "Playbacks", "content_id": "Content ID"})
    )
    watch_by_c = duration.watch_seconds_by(dfc, "content_id").reset_index()
    watch_by_c.columns = ["Content ID", "Watch Seconds"]
    bw_by_c = (
        dfc.groupby("content_id")["object_size"].sum().div(1024**2).reset_index()
        .rename(columns={"object_size": "BW (MB)", "content_id": "Content ID"})
    )
    cm = (
        content_plays.merge(watch_by_c, on="Content ID", how="outer")
        .merge(bw_by_c, on="Content ID", how="outer").fillna(0)
    )
    cm["Content ID"] = cm["Content ID"].astype(str)
    cm["Watch (Min)"] = cm["Watch Seconds"].apply(indian_format.humanize_minutes)
    cm["Bandwidth"]   = cm["BW (MB)"].apply(lambda b: f"{b:.2f} MB")
    cm = cm.sort_values("Playbacks", ascending=False)

    col_t, col_m, col_b = st.columns(3)
    with col_t:
        st.markdown("**By Playbacks**")
        fig_cp = px.bar(cm.head(10), x="Playbacks", y="Content ID", orientation="h",
                        color_discrete_sequence=[brand.ORANGE])
        fig_cp.update_layout(**brand.chart_layout("Top 10 by Playbacks"))
        fig_cp.update_yaxes(autorange="reversed", type="category")
        st.plotly_chart(fig_cp, use_container_width=True)
    with col_m:
        st.markdown("**By Watch (Min)**")
        fig_cm = px.bar(cm.sort_values("Watch Seconds", ascending=False).head(10),
                        x="Watch Seconds", y="Content ID", orientation="h",
                        color_discrete_sequence=[brand.ORANGE_WARM])
        fig_cm.update_layout(**brand.chart_layout("Top 10 by Watch Time"))
        fig_cm.update_yaxes(autorange="reversed", type="category")
        st.plotly_chart(fig_cm, use_container_width=True)
    with col_b:
        st.markdown("**By Bandwidth**")
        fig_cb = px.bar(cm.sort_values("BW (MB)", ascending=False).head(10),
                        x="BW (MB)", y="Content ID", orientation="h",
                        color_discrete_sequence=["#4F3690"])
        fig_cb.update_layout(**brand.chart_layout("Top 10 by Bandwidth"))
        fig_cb.update_yaxes(autorange="reversed", type="category")
        st.plotly_chart(fig_cb, use_container_width=True)

    st.markdown('<div class="section-title">Content Detail Table</div>', unsafe_allow_html=True)
    st.dataframe(cm[["Content ID", "Playbacks", "Watch (Min)", "Bandwidth"]], width="stretch", hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 – GEO
# ════════════════════════════════════════════════════════════════════════════════
with tab_geo:
    st.markdown('<div class="section-title">Geographic Distribution (India)</div>', unsafe_allow_html=True)
    st.caption(
        "■ Cities/states with 0 min watch time made only failed (4xx) requests — "
        "no content was delivered. A single client IP may appear in multiple "
        "cities if the CDN edge routing resolved it differently across requests."
    )

    df_in_geo = df[df["country"] == "IN"].copy()

    state_plays = (
        df_in_geo[df_in_geo["asset_kind"] == "master_manifest"]
        .groupby("state")["session_id"].nunique().reset_index()
        .rename(columns={"session_id": "Playbacks", "state": "State"})
    )
    state_watch = duration.watch_seconds_by(df_in_geo, "state").reset_index()
    state_watch.columns = ["State", "Watch Seconds"]
    state_geo = state_plays.merge(state_watch, on="State", how="outer").fillna(0)
    state_geo["Watch (Min)"] = state_geo["Watch Seconds"].apply(indian_format.humanize_minutes)
    state_geo = state_geo.sort_values("Playbacks", ascending=False)

    col_map, col_tab = st.columns([3, 2])
    with col_map:
        if not state_geo.empty:
            fig_geo = px.bar(state_geo.head(15), x="Playbacks", y="State", orientation="h",
                             color="Playbacks",
                             color_continuous_scale=[[0, brand.SALMON], [1, brand.ORANGE]])
            fig_geo.update_layout(**brand.chart_layout("Playbacks by State (Top 15)"))
            fig_geo.update_yaxes(autorange="reversed")
            fig_geo.update_coloraxes(showscale=False)
            st.plotly_chart(fig_geo, use_container_width=True)
    with col_tab:
        st.markdown("**State Summary**")
        st.dataframe(state_geo[["State", "Playbacks", "Watch (Min)"]], width="stretch", hide_index=True)

    # City breakdown — exclude "Unknown" from chart, keep in table
    st.markdown('<div class="section-title">City Breakdown</div>', unsafe_allow_html=True)
    city_plays = (
        df_in_geo[df_in_geo["asset_kind"] == "master_manifest"]
        .groupby(["city", "state"])["session_id"].nunique().reset_index()
        .rename(columns={"session_id": "Playbacks"})
    )
    city_watch = duration.watch_seconds_by(df_in_geo, "city").reset_index()
    city_watch.columns = ["city", "Watch Seconds"]
    city_bw = (
        df_in_geo.groupby("city")["object_size"].sum().div(1024**2).reset_index()
        .rename(columns={"object_size": "BW (MB)"})
    )
    city_tbl = (
        city_plays.merge(city_watch, on="city", how="outer")
        .merge(city_bw, on="city", how="outer").fillna(0)
    )
    city_tbl["Watch (Min)"] = city_tbl["Watch Seconds"].apply(indian_format.humanize_minutes)
    city_tbl = city_tbl.rename(columns={"city": "City", "state": "State"}).sort_values("Watch Seconds", ascending=False)

    # Chart: exclude "Unknown" city
    city_chart = city_tbl[city_tbl["City"] != "Unknown"].head(15)
    fig_city = px.bar(city_chart, x="Playbacks", y="City", orientation="h",
                      color_discrete_sequence=[brand.ORANGE_WARM])
    fig_city.update_layout(**brand.chart_layout("Top Cities by Playbacks (excl. Unknown)"))
    fig_city.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_city, use_container_width=True)

    st.dataframe(city_tbl[["City", "State", "Playbacks", "Watch (Min)", "BW (MB)"]], width="stretch", hide_index=True)
    st.caption("'Unknown' city = CDN could not resolve a city name for that IP (field 23 was '-' in the raw log).")

    st.markdown('<div class="section-title">■ Non-IN Traffic (Bot / Probe)</div>', unsafe_allow_html=True)
    df_non_in2 = df_raw[df_raw["country"] != "IN"]
    if not df_non_in2.empty:
        non_in2 = (
            df_non_in2.groupby(["country", "city"])
            .agg(Requests=("client_ip", "count"), IPs=("client_ip", "nunique"))
            .sort_values("Requests", ascending=False).reset_index()
            .rename(columns={"country": "Country", "city": "City"})
        )
        st.dataframe(non_in2, width="stretch", hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 – SESSIONS
# ════════════════════════════════════════════════════════════════════════════════
with tab_sessions:
    st.markdown('<div class="section-title">Session Explorer</div>', unsafe_allow_html=True)

    st.info(
        "**Requests** = total HTTP fetches by the player in that session "
        "(master manifest + variant manifests + init fragments + video segments + audio segments). "
        "A 5-segment playback makes ~12 requests; higher numbers mean longer or re-buffering sessions.  \n"
        "**Segments** = distinct audio segment numbers delivered — each worth 8 seconds of watch time."
    )

    search = st.text_input("Search session ID or content ID", placeholder="e.g. 23334")

    sess_watch = duration.watch_seconds_by_session(df)
    sess_summary = (
        df.groupby("session_id")
        .agg(
            client_ip=("client_ip", "first"),
            country=("country", "first"),
            city=("city", "first"),
            content_ids=("content_id", lambda x: ", ".join(
                sorted(v for v in x.dropna().unique() if v not in ("", "Unknown"))
            )),
            requests=("request_path", "count"),
            errors=("http_status", lambda x: int((x >= 400).sum())),
            first_seen=("request_ts_ist", "min"),
            last_seen=("request_ts_ist", "max"),
        )
        .reset_index()
    )
    sess_summary = sess_summary.merge(
        sess_watch[["session_id", "watch_seconds", "segment_count"]], on="session_id", how="left"
    )
    sess_summary["watch_seconds"]  = sess_summary["watch_seconds"].fillna(0)
    sess_summary["segment_count"]  = sess_summary["segment_count"].fillna(0).astype(int)
    sess_summary["Watch (Min)"]    = sess_summary["watch_seconds"].apply(indian_format.humanize_minutes)
    sess_summary["First Seen"]     = sess_summary["first_seen"].apply(indian_format.format_datetime)
    sess_summary["Last Seen"]      = sess_summary["last_seen"].apply(indian_format.format_datetime)
    sess_summary["content_ids"]    = sess_summary["content_ids"].replace("", "—")

    def _label_session(sid: str) -> str:
        if sid.startswith("anon::"):
            parts = sid.split("::")
            return f"Anonymous ({parts[1] if len(parts) > 1 else '?'})"
        return sid

    sess_summary["Session"] = sess_summary["session_id"].apply(_label_session)

    if search:
        mask = (
            sess_summary["session_id"].str.contains(search, case=False, na=False) |
            sess_summary["content_ids"].str.contains(search, case=False, na=False)
        )
        sess_summary = sess_summary[mask]

    display = sess_summary[[
        "Session", "client_ip", "country", "city",
        "content_ids", "Watch (Min)", "segment_count",
        "requests", "errors", "First Seen", "Last Seen",
    ]].rename(columns={
        "client_ip": "Client IP", "country": "Country", "city": "City",
        "content_ids": "Content IDs", "segment_count": "Segments",
        "requests": "Requests", "errors": "Errors",
    })

    st.dataframe(display, width="stretch", hide_index=True)
    st.caption(f"■ {len(display):,} sessions shown")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 – BANDWIDTH & PERFORMANCE
# ════════════════════════════════════════════════════════════════════════════════
with tab_bw:
    st.markdown('<div class="section-title">Object Size Distribution</div>', unsafe_allow_html=True)
    df_bw = df[df["object_size"].notna() & (df["object_size"] > 0)].copy()

    col_hist, col_lat = st.columns(2)
    with col_hist:
        fig_hist = px.histogram(df_bw, x="object_size", nbins=50,
                                labels={"object_size": "Object Size (bytes)"},
                                color_discrete_sequence=[brand.ORANGE])
        fig_hist.update_layout(**brand.chart_layout("Object Size Histogram"))
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_lat:
        df_lat = df[df["turn_around_ms"].notna() & (df["turn_around_ms"] >= 1)].copy()
        if not df_lat.empty:
            df_lat["hour"] = df_lat["request_ts_ist"].dt.floor("h")
            lat_h = (
                df_lat.groupby("hour")["turn_around_ms"]
                .agg(p50=lambda x: x.quantile(0.5), p95=lambda x: x.quantile(0.95))
                .reset_index()
            )
            fig_lat = go.Figure()
            fig_lat.add_trace(go.Scatter(x=lat_h["hour"], y=lat_h["p50"], name="p50 ms",
                                         line=dict(color=brand.ORANGE)))
            fig_lat.add_trace(go.Scatter(x=lat_h["hour"], y=lat_h["p95"], name="p95 ms",
                                         line=dict(color=brand.AMBER, dash="dash")))
            fig_lat.update_layout(**brand.chart_layout(
                "Edge Latency p50 / p95",
                xaxis_title="Hour (IST)", yaxis_title="Turn-around time (ms)"
            ))
            st.plotly_chart(fig_lat, use_container_width=True)

    st.markdown('<div class="section-title">Cache Hit Ratio Over Time</div>', unsafe_allow_html=True)
    df_cache = df[df["cache_status"].notna()].copy()
    if not df_cache.empty:
        df_cache["hour"] = df_cache["request_ts_ist"].dt.floor("h")
        cache_h = (
            df_cache.groupby("hour")
            .apply(lambda x: (x["cache_status"] == 1).sum() / len(x) * 100, include_groups=False)
            .reset_index().rename(columns={0: "Cache Hit %", "hour": "Hour (IST)"})
        )
        fig_cache = px.line(cache_h, x="Hour (IST)", y="Cache Hit %",
                            color_discrete_sequence=[brand.GREEN])
        fig_cache.update_layout(**brand.chart_layout("Cache Hit % per Hour"))
        fig_cache.add_hline(y=50, line_dash="dot", line_color=brand.AMBER, annotation_text="50% threshold")
        st.plotly_chart(fig_cache, use_container_width=True)

    df_mbps = df[df["mbps"].notna()]
    if not df_mbps.empty:
        st.markdown('<div class="section-title">Per-Row Throughput (Mbps)</div>', unsafe_allow_html=True)
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Avg Mbps", f"{df_mbps['mbps'].mean():.3f}")
        col_m2.metric("p95 Mbps", f"{df_mbps['mbps'].quantile(0.95):.3f}")
        col_m3.metric("Max Mbps", f"{df_mbps['mbps'].max():.3f}")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 6 – RAW EXPLORER
# ════════════════════════════════════════════════════════════════════════════════
with tab_raw:
    st.markdown('<div class="section-title">Raw Parsed Data Explorer</div>', unsafe_allow_html=True)

    all_cols = df.columns.tolist()
    default_cols = [c for c in [
        "request_ts_ist", "session_id", "client_ip", "country", "city", "state",
        "http_status", "asset_kind", "content_id", "segment_no",
        "object_size", "cache_status", "turn_around_ms", "playback_seconds",
    ] if c in all_cols]
    sel_cols = st.multiselect("Columns to display", all_cols, default=default_cols)

    page_size   = st.select_slider("Rows per page", [25, 50, 100, 250, 500], value=100)
    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    page        = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    start, end  = (page - 1) * page_size, page * page_size

    df_page = df[sel_cols].iloc[start:end] if sel_cols else df.iloc[start:end]
    st.dataframe(df_page, width="stretch", hide_index=True)
    st.caption(f"■ Rows {start+1}–{min(end, len(df))} of {len(df):,} | Page {page}/{total_pages}")

    csv = (df[sel_cols] if sel_cols else df).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "airtel_cdn_parsed.csv", "text/csv")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hm-footer"><span>Confidential | Hungama Digital Media Entertainment Pvt. Ltd.</span>'
    '<span>Airtel CDN Analytics v1.0</span></div>',
    unsafe_allow_html=True,
)
