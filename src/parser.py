"""Airtel CDN log parser.

Reads the space-delimited 24-field Akamai edge log and returns a typed pandas
DataFrame with 5 additional derived columns.  This is the ONLY place that reads
raw log lines; the dashboard never touches the file directly.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

FIELDS = [
    "stream_version", "cp_code", "client_ip", "http_status", "protocol",
    "request_host", "request_method", "request_path", "user_agent",
    "x_forwarded_for", "error_code", "request_ts_epoch", "turn_around_ms",
    "object_size", "uncompressed_size", "query_string", "cache_status",
    "country", "cacheable", "cmcd", "delivery_format", "delivery_type",
    "city", "state",
]

INT_FIELDS = ("turn_around_ms", "object_size", "cache_status",
              "cacheable", "delivery_format", "delivery_type")

PATH_RE = re.compile(
    r"partners/airtel/([^/]+)/c/[^/]+/[^/]+/trailer/content/(\d+)_,"
)
ASSET_RE = re.compile(
    r"/(index\.m3u8"
    r"|index-f\d+-(?:v1|a1)\.m3u8"
    r"|init-f\d+-(?:v1|a1)\.mp4"
    r"|segment-(\d+)-f\d+-(v1|a1)\.m4s)$"
)
IST = ZoneInfo("Asia/Kolkata")


def _bucket_30min(ts_ist: datetime, ip: str, content_id: str) -> str:
    bucket = ts_ist.replace(minute=(ts_ist.minute // 30) * 30, second=0, microsecond=0)
    return f"anon::{ip}::{content_id}::{bucket.strftime('%Y%m%d%H%M')}"


def parse_line(line: str) -> dict | None:
    line = line.lstrip("​").strip()
    if not line:
        return None

    parts = line.split(" ", 23)
    if len(parts) != 24:
        return None

    row = dict(zip(FIELDS, parts))

    for k in INT_FIELDS:
        v = row.get(k, "-")
        row[k] = int(v) if v not in ("-", "") and v.lstrip("-").isdigit() else None

    try:
        row["request_ts_ist"] = datetime.fromtimestamp(float(row["request_ts_epoch"]), IST)
    except (ValueError, TypeError):
        return None

    # --- derive session_id, content_id ---
    m = PATH_RE.search(row["request_path"])
    raw = m.group(1) if m else None
    content = m.group(2) if m else None
    row["session_id_raw"] = raw
    row["content_id"] = content

    if raw and raw != "session":
        row["session_id"] = raw
    else:
        row["session_id"] = _bucket_30min(
            row["request_ts_ist"], row["client_ip"], content or ""
        )

    # --- derive asset_kind, segment_no, playback_seconds ---
    a = ASSET_RE.search(row["request_path"])
    if not a:
        row["asset_kind"] = "other"
        row["segment_no"] = None
        row["playback_seconds"] = 0
    else:
        token = a.group(1)
        seg_no = a.group(2)
        track = a.group(3)

        if token == "index.m3u8":
            row["asset_kind"] = "master_manifest"
        elif token.startswith("index-"):
            row["asset_kind"] = "variant_manifest"
        elif token.startswith("init-"):
            row["asset_kind"] = "init_fragment"
        elif track == "v1":
            row["asset_kind"] = "video_segment"
        else:
            row["asset_kind"] = "audio_segment"

        row["segment_no"] = int(seg_no) if seg_no else None
        row["playback_seconds"] = 8 if row["asset_kind"] == "audio_segment" else 0

    return row


def parse_file(path: str | Path) -> pd.DataFrame:
    """Parse the full log file and return a typed DataFrame."""
    path = Path(path)
    rows = []
    error_count = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            r = parse_line(line)
            if r:
                rows.append(r)
            elif line.strip():
                error_count += 1

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # Type cleanup
    df["http_status"] = pd.to_numeric(df["http_status"], errors="coerce").astype("Int64")
    df["stream_version"] = pd.to_numeric(df["stream_version"], errors="coerce").astype("Int64")
    df["asset_kind"] = df["asset_kind"].astype("category")
    df["country"] = df["country"].str.upper().str.strip()
    df["city"] = df["city"].str.title().str.strip()
    df["state"] = df["state"].str.title().str.strip()

    # Normalise dash-only strings to None
    for col in ("x_forwarded_for", "error_code", "cmcd", "uncompressed_size", "query_string"):
        if col in df.columns:
            df[col] = df[col].replace("-", None)

    return df


def save_parquet(df: pd.DataFrame, out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)


def load_parquet(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_stats(df: pd.DataFrame, out_path: str | Path) -> None:
    """Write a JSON sidecar with parser statistics."""
    out_path = Path(out_path)
    ts = df["request_ts_ist"]
    stats = {
        "row_count": len(df),
        "error_count": int((df["http_status"] >= 400).sum()) if "http_status" in df else 0,
        "distinct_sessions": int(df["session_id"].nunique()),
        "distinct_contents": int(df["content_id"].nunique()),
        "time_range": {
            "start": str(ts.min()),
            "end": str(ts.max()),
        },
    }
    out_path.write_text(json.dumps(stats, indent=2))


if __name__ == "__main__":
    import sys

    log_path = sys.argv[1] if len(sys.argv) > 1 else "data/Airtel_logs_2.json"
    print(f"Parsing {log_path} …")
    df = parse_file(log_path)
    print(f"  Rows parsed : {len(df):,}")
    print(f"  Columns     : {list(df.columns)}")

    out_parquet = Path(log_path).parent / "parsed.parquet"
    save_parquet(df, out_parquet)
    print(f"  Parquet     : {out_parquet}")

    out_stats = Path(log_path).parent / "parser_stats.json"
    write_stats(df, out_stats)
    print(f"  Stats       : {out_stats}")
