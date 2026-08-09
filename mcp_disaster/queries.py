"""Pure pandas query functions for natural disaster data.

Separated from server.py so unit tests can call these functions directly
without starting an MCP subprocess (see ASR-3).
"""
from __future__ import annotations

import pandas as pd

_VALID_GROUP_BY = frozenset(["disaster_type", "country", "continent", "year", "region"])
_VALID_METRICS = frozenset(["total_deaths", "total_affected", "event_count"])

_DISPLAY_COLS = ["year", "disaster_type", "country", "region", "continent",
                 "total_deaths", "total_affected"]


def search_disasters_impl(
    df: pd.DataFrame,
    disaster_type: str | None = None,
    country: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    limit: int = 20,
) -> str:
    """Filter disaster records and return as formatted text.

    Args:
        df: DataFrame with normalized column names (lowercase + underscore).
        disaster_type: Partial match against 'disaster_type' column (case-insensitive).
        country: Partial match against 'country' column (case-insensitive).
        year_min: Minimum year (inclusive). None = no lower bound.
        year_max: Maximum year (inclusive). None = no upper bound.
        limit: Maximum rows to return.

    Returns:
        Formatted table string, or a "no records found" message.
    """
    mask = pd.Series([True] * len(df), index=df.index)

    if disaster_type and "disaster_type" in df.columns:
        mask &= df["disaster_type"].str.lower().str.contains(
            disaster_type.lower(), na=False, regex=False
        )
    if country and "country" in df.columns:
        mask &= df["country"].str.lower().str.contains(
            country.lower(), na=False, regex=False
        )
    if year_min is not None and "year" in df.columns:
        mask &= df["year"] >= year_min
    if year_max is not None and "year" in df.columns:
        mask &= df["year"] <= year_max

    result = df[mask].head(limit)
    if result.empty:
        return "No matching disaster records found."

    display_cols = [c for c in _DISPLAY_COLS if c in result.columns]
    subset: pd.DataFrame = result[display_cols]  # type: ignore[assignment]
    return subset.to_string(index=False)


def get_disaster_statistics_impl(
    df: pd.DataFrame,
    group_by: str = "disaster_type",
    metric: str = "total_deaths",
    top_n: int = 10,
) -> str:
    """Aggregate disaster statistics by a given dimension.

    Args:
        df: DataFrame with normalized column names.
        group_by: Column to group by. Valid: 'disaster_type', 'country',
            'continent', 'year', 'region'.
        metric: Aggregation metric. Valid: 'total_deaths', 'total_affected',
            'event_count'.
        top_n: Number of top groups to return.

    Returns:
        Aggregated statistics as a formatted table string, or an error message.
    """
    if group_by not in df.columns:
        available = [c for c in _VALID_GROUP_BY if c in df.columns]
        return f"Unknown group_by '{group_by}'. Available: {', '.join(sorted(available))}"

    if metric == "event_count":
        counts = df.groupby(group_by).size().nlargest(top_n)  # type: ignore[union-attr]
        result = pd.DataFrame(  # type: ignore
            list(zip(counts.index, counts.values.tolist())),
            columns=[group_by, "event_count"],
        )
    elif metric in df.columns:
        agg: pd.Series = df.groupby(group_by)[metric].sum()  # type: ignore[assignment]
        result = agg.nlargest(top_n).reset_index()
        result[metric] = result[metric].fillna(0).astype(int)
    else:
        available_metrics = sorted(
            m for m in _VALID_METRICS if m == "event_count" or m in df.columns
        )
        return f"Unknown metric '{metric}'. Available: {', '.join(available_metrics)}"

    return result.to_string(index=False)
