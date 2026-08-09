# mcp-disaster-server

MCP server for querying the Kaggle "All Natural Disasters 1900-2021 / EOSDIS" CSV dataset via pandas.

Exposes two tools over the stdio MCP protocol:
- `search_disasters` — filter records by disaster type, country, and year range
- `get_disaster_statistics` — aggregate statistics by dimension (country, continent, year, etc.)

## Usage with uvx

```bash
DISASTER_CSV_PATH=/path/to/natural_disasters.csv uvx --from . mcp-disaster-server
```

Or if published to PyPI:

```bash
DISASTER_CSV_PATH=/path/to/natural_disasters.csv uvx mcp-disaster-server
```

## Install as editable package (for development)

```bash
pip install -e .
```

After installation the entry point is available as:

```bash
DISASTER_CSV_PATH=/path/to/natural_disasters.csv mcp-disaster-server
```

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `DISASTER_CSV_PATH` | Yes | Path to the EOSDIS natural disasters CSV |

## Data

Download the CSV from Kaggle: *All Natural Disasters 1900-2021 / EOSDIS* dataset.
The server normalizes column names at startup (lowercase, underscores, no punctuation).
