"""Duration computation using the 8-second-per-segment rule.

The accurate formula: 8 × count(DISTINCT (session_id, content_id, segment_no))
anchored on audio segments (asset_kind == 'audio_segment').
If a session has no audio segments, fall back to any .m4s segment with the
same DISTINCT collapse.
"""

import pandas as pd


def _audio_distinct(df: pd.DataFrame) -> pd.DataFrame:
    audio = df[df["asset_kind"] == "audio_segment"].copy()
    return audio.drop_duplicates(subset=["session_id", "content_id", "segment_no"])


def _video_distinct(df: pd.DataFrame) -> pd.DataFrame:
    segs = df[df["asset_kind"].isin(["audio_segment", "video_segment"])].copy()
    return segs.drop_duplicates(subset=["session_id", "content_id", "segment_no"])


def collapse_distinct(df: pd.DataFrame) -> pd.DataFrame:
    """Return the de-duplicated segment rows used for duration accounting.

    Prefers audio spine; falls back to any segment if audio is absent.
    Each row in the result contributes exactly 8 seconds.
    """
    audio = _audio_distinct(df)
    if len(audio) > 0:
        return audio

    return _video_distinct(df)


def total_watch_seconds(df: pd.DataFrame) -> int:
    """Total platform watch time in seconds (DISTINCT-collapsed)."""
    collapsed = collapse_distinct(df)
    return int(collapsed["playback_seconds"].where(
        collapsed["asset_kind"] == "audio_segment", 8
    ).sum())


def watch_seconds_by(df: pd.DataFrame, group_col: str | list[str]) -> pd.Series:
    """Watch seconds grouped by one or more columns (e.g. content_id, city)."""
    collapsed = collapse_distinct(df)
    collapsed = collapsed.copy()
    collapsed["_secs"] = 8
    return collapsed.groupby(group_col)["_secs"].sum().rename("watch_seconds")


def watch_seconds_by_session(df: pd.DataFrame) -> pd.DataFrame:
    """Per-session watch time summary."""
    collapsed = collapse_distinct(df)
    collapsed = collapsed.copy()
    collapsed["_secs"] = 8
    return (
        collapsed.groupby("session_id")
        .agg(
            watch_seconds=("_secs", "sum"),
            segment_count=("segment_no", "nunique"),
            content_ids=("content_id", lambda x: list(x.dropna().unique())),
        )
        .reset_index()
    )
