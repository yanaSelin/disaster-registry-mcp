"""Natural disaster query MCP server.

Reads the Kaggle 'All Natural Disasters 1900-2021 EOSDIS' CSV via pandas.
Exposes two tools via the MCP stdio protocol:
  - search_disasters: filter records by type, country, year range
  - get_disaster_statistics: aggregate by dimension/metric

Configure the CSV path via the DISASTER_CSV_PATH env var.
Entry point (used by uvx): mcp-disaster-server
"""
import os
from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP

from .queries import get_disaster_statistics_impl, search_disasters_impl

DATA_PATH = Path(os.environ.get("DISASTER_CSV_PATH", "data/natural_disasters.csv"))

mcp = FastMCP("disaster-server")

_df: pd.DataFrame | None = None


def _get_df() -> pd.DataFrame:
    global _df
    if _df is None:
        raw = pd.read_csv(DATA_PATH)
        raw.columns = pd.Index([
            c.strip().lower()
            .replace(" ", "_")
            .replace("(", "").replace(")", "")
            .replace("'", "").replace(",", "")
            for c in raw.columns
        ])
        _df = raw
    return _df


@mcp.tool()
async def search_disasters(
    disaster_type: str = "",
    country: str = "",
    year_min: int = 0,
    year_max: int = 0,
    limit: int = 20,
) -> str:
    """Search natural disaster records with optional filters.

    Args:
        disaster_type: Category like 'Flood', 'Earthquake', 'Storm', 'Cyclone'.
            Empty string means no filter.
        country: Country name substring, e.g. 'China', 'United States'. Empty = any.
        year_min: Start year inclusive (e.g. 2000). 0 means no lower bound.
        year_max: End year inclusive (e.g. 2021). 0 means no upper bound.
        limit: Maximum records to return (default 20).

    Returns:
        Matching disaster records as a formatted table, or a no-results message.
    """
    return search_disasters_impl(
        _get_df(),
        disaster_type=disaster_type or None,
        country=country or None,
        year_min=year_min or None,
        year_max=year_max or None,
        limit=limit,
    )


@mcp.tool()
async def get_disaster_statistics(
    group_by: str = "disaster_type",
    metric: str = "total_deaths",
    top_n: int = 10,
) -> str:
    """Get aggregate natural disaster statistics.

    Args:
        group_by: Grouping dimension. Valid values: 'disaster_type', 'country',
            'continent', 'year', 'region'.
        metric: Aggregation. Valid values: 'total_deaths', 'total_affected',
            'event_count'.
        top_n: Number of top groups to return (default 10).

    Returns:
        Aggregated statistics as a formatted table.
    """
    return get_disaster_statistics_impl(
        _get_df(),
        group_by=group_by,
        metric=metric,
        top_n=top_n,
    )


def run() -> None:
    """Entry point for uvx / pyproject.toml [project.scripts]."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
