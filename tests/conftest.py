"""Shared pytest fixtures."""
from pathlib import Path

import pandas as pd
import pytest

_SAMPLE_CSV = Path(__file__).parent / "natural_disasters_sample.csv"


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """30-row test DataFrame with normalized column names (same as MCP server)."""
    raw = pd.read_csv(_SAMPLE_CSV)
    raw.columns = pd.Index([
        c.strip().lower()
        .replace(" ", "_")
        .replace("(", "").replace(")", "")
        .replace("'", "").replace(",", "")
        for c in raw.columns
    ])
    return raw
