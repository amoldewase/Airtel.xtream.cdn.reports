"""Enrichment: bot detection, geo cleanup, content metadata stub."""

import pandas as pd

# Known non-IN countries that are bot/probe traffic in this dataset
BOT_COUNTRIES = {"JP", "MY", "US", "GB", "SG", "HK", "DE", "FR", "NL", "AU"}


def tag_traffic_type(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'traffic_type' column: 'organic' (IN) or 'bot_probe' (non-IN)."""
    df = df.copy()
    df["traffic_type"] = df["country"].apply(
        lambda c: "organic" if str(c).upper() == "IN" else "bot_probe"
    )
    return df


def clean_geo(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise city/state to Title Case; replace missing with 'Unknown'."""
    df = df.copy()
    df["city"] = df["city"].fillna("Unknown").str.title().str.strip()
    df["state"] = df["state"].fillna("Unknown").str.title().str.strip()
    df["city"] = df["city"].replace("-", "Unknown").replace("", "Unknown")
    df["state"] = df["state"].replace("-", "Unknown").replace("", "Unknown")
    return df


def compute_mbps(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-row 'mbps' column: object_size * 8 / turn_around_ms / 1000.

    Rows with turn_around_ms < 1 are excluded (cache hits return 0/1 ms).
    """
    df = df.copy()
    valid = df["turn_around_ms"].notna() & (df["turn_around_ms"] >= 1)
    df["mbps"] = None
    df.loc[valid, "mbps"] = (
        df.loc[valid, "object_size"] * 8
        / df.loc[valid, "turn_around_ms"]
        / 1000
    )
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Run all enrichment steps and return the augmented DataFrame."""
    df = tag_traffic_type(df)
    df = clean_geo(df)
    df = compute_mbps(df)
    return df
