"""Sessions page - searchable session table with known-session callout."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from src import brand, duration, enrich, indian_format, parser

st.set_page_config(page_title="Sessions | Airtel CDN Analytics", layout="wide")
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
    '<div class="hungama-header"><h1>&#9654; Session Explorer</h1></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<p style="color:#FF6623;font-weight:700;">&#9632; Filters</p>', unsafe_allow_html=True)
    countries = sorted(df_raw["country"].dropna().unique())
    sel_country = st.multiselect("Country", countries, default=["IN"])
    show_anon = st.checkbox("Include anonymous sessions", value=True)

df = df_raw[df_raw["country"].isin(sel_country)] if sel_country else df_raw
if not show_anon:
    df = df[~df["session_id"].str.startswith("anon::")]

search = st.text_input("Search by session ID or content ID", placeholder="e.g. 23334")

sess_watch = duration.watch_seconds_by_session(df)

sess_summary = (
    df.groupby("session_id")
    .agg(
        client_ip=("client_ip", "first"),
        country=("country", "first"),
        city=("city", "first"),
        state=("state", "first"),
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
    sess_watch[["session_id", "watch_seconds", "segment_count"]],
    on="session_id", how="left",
)
sess_summary["watch_seconds"] = sess_summary["watch_seconds"].fillna(0)
sess_summary["segment_count"] = sess_summary["segment_count"].fillna(0).astype(int)
sess_summary["Watch (Min)"] = sess_summary["watch_seconds"].apply(indian_format.humanize_minutes)
sess_summary["First Seen (IST)"] = sess_summary["first_seen"].apply(indian_format.format_datetime)
sess_summary["Last Seen (IST)"] = sess_summary["last_seen"].apply(indian_format.format_datetime)
sess_summary["content_ids"] = sess_summary["content_ids"].replace("", "—")


def _label_session(sid: str) -> str:
    if sid.startswith("anon::"):
        parts = sid.split("::")
        ip = parts[1] if len(parts) > 1 else "unknown"
        return f"Anonymous ({ip})"
    return sid


sess_summary["Session"] = sess_summary["session_id"].apply(_label_session)

if search:
    mask = (
        sess_summary["session_id"].str.contains(search, case=False, na=False) |
        sess_summary["content_ids"].str.contains(search, case=False, na=False)
    )
    sess_summary = sess_summary[mask]

display = sess_summary[[
    "Session", "client_ip", "country", "city", "state",
    "content_ids", "Watch (Min)", "segment_count",
    "requests", "errors", "First Seen (IST)", "Last Seen (IST)",
]].rename(columns={
    "client_ip": "Client IP",
    "country": "Country",
    "city": "City",
    "state": "State",
    "content_ids": "Content IDs",
    "segment_count": "Segments",
    "requests": "Requests",
    "errors": "Errors",
}).sort_values("Segments", ascending=False)

st.markdown(
    f'<div class="section-title">Sessions ({len(display):,} shown)</div>',
    unsafe_allow_html=True,
)
st.dataframe(display, width="stretch", hide_index=True)

csv = display.to_csv(index=False).encode("utf-8")
st.download_button("Download Sessions CSV", csv, "sessions_report.csv", "text/csv")

# ── Known session IDs acceptance check ─────────────────────────────────────────
known = ["jklhlkajd888", "kjkjk4333", "jkljlk0000", "njknkj999", "23334"]
st.markdown('<div class="section-title">■ Known Session IDs (PRD Acceptance Check)</div>', unsafe_allow_html=True)
all_raw = df_raw["session_id_raw"].dropna().unique().tolist()
found_any = False
for sid in known:
    if sid in all_raw:
        row = sess_summary[sess_summary["session_id"] == sid]
        if not row.empty:
            r = row.iloc[0]
            st.success(f"&#9632; {sid}  —  Watch: {r['Watch (Min)']}  |  Segments: {int(r['segment_count'])}  |  Content: {r['content_ids']}")
        found_any = True
if not found_any:
    st.info("Session IDs from PRD examples (jklhlkajd888 etc.) are not in this log batch. "
            f"This batch contains {len(all_raw)} session token(s): {', '.join(sorted(str(x) for x in all_raw))}")

st.markdown(
    '<div class="hm-footer"><span>Confidential | Hungama Digital Media Entertainment Pvt. Ltd.</span><span>Sessions</span></div>',
    unsafe_allow_html=True,
)
