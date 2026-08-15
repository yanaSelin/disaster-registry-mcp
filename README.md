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
| `KAGGLE_API_TOKEN` | First run only | Kaggle API token for auto-downloading the CSV on first launch. Not needed if the CSV already exists at `DISASTER_CSV_PATH`. |
| `DISASTER_CSV_PATH` | No | Override the CSV path. Defaults to `~/.mcp-disaster-server/natural_disasters.csv`. Useful in tests or CI to point at the 30-row sample fixture. |

## Data

The server auto-downloads the Kaggle *All Natural Disasters 1900-2021 / EOSDIS* dataset
on first launch (requires `KAGGLE_API_TOKEN`) and caches it at
`~/.mcp-disaster-server/natural_disasters.csv`. Subsequent runs reuse the cached file.
Column names are normalized at startup (lowercase, underscores, no punctuation).

See [docs/architecture.md](docs/architecture.md) for design decisions.
