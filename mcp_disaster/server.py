"""Natural disaster query MCP server.

Reads the Kaggle 'All Natural Disasters 1900-2021 EOSDIS' CSV via pandas.
Exposes two tools via the MCP stdio protocol:
  - search_disasters: filter records by type, country, year range
  - get_disaster_statistics: aggregate by dimension/metric

Configure the CSV path via the DISASTER_CSV_PATH env var.
Entry point (used by uvx): mcp-disaster-server
"""
import os
import sys
from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP

from .queries import get_disaster_statistics_impl, search_disasters_impl

_KAGGLE_DATASET = "brsdincer/all-natural-disasters-19002021-eosdis"

# Persistent cache in user home — survives across uvx runs.
# Override with DISASTER_CSV_PATH for testing.
DATA_PATH = Path(
    os.environ.get("DISASTER_CSV_PATH")
    or str(Path.home() / ".mcp-disaster-server" / "natural_disasters.csv")
)


def _ensure_csv(path: Path) -> None:
    """Download the disaster CSV from Kaggle if not present. Raises on failure."""
    if path.exists():
        return

    api_token = os.environ.get("KAGGLE_API_TOKEN")
    if not api_token:
        raise RuntimeError(
            f"Disaster CSV not found at {path}. "
            "Set KAGGLE_API_TOKEN to auto-download, "
            "or place the CSV at that path manually."
        )

    try:
        import kaggle  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("kaggle package not installed — run: pip install kaggle") from exc

    os.environ["KAGGLE_TOKEN"] = api_token
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[disaster-server] Downloading {_KAGGLE_DATASET} from Kaggle...", file=sys.stderr)
    kaggle.api.authenticate()
    kaggle.api.dataset_download_files(_KAGGLE_DATASET, path=str(path.parent), unzip=True, quiet=True)

    csvs = [f for f in path.parent.glob("*.csv") if f != path]
    if csvs and not path.exists():
        csvs[0].rename(path)
    print(f"[disaster-server] Dataset saved to {path}", file=sys.stderr)


_ensure_csv(DATA_PATH)

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

    Covers global natural disaster events from 1900 to 2021 (EOSDIS dataset).
    Does NOT include events after 2021 — use news tools for recent disasters.

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
    """Get aggregate natural disaster statistics from the 1900–2021 EOSDIS dataset.

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
