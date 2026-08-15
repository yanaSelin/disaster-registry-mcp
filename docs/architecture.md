# Architecture Design — mcp-disaster-server

## System Overview

A single-purpose MCP server that exposes natural disaster query capabilities over the
stdio protocol. Backed by the Kaggle "All Natural Disasters 1900-2021 / EOSDIS" CSV,
queried in-process via pandas. Designed as a standalone installable package so any MCP
host can launch it via `uvx` without a local checkout.

Two tools:
- **`search_disasters`** — filter records by disaster type, country, year range; returns a
  formatted table or a "no results" message
- **`get_disaster_statistics`** — aggregate by dimension (`disaster_type`, `country`,
  `continent`, `year`, `region`) and metric (`total_deaths`, `total_affected`,
  `event_count`); returns top-N groups as a formatted table

---

## Package Structure

```
mcp_disaster/
├── queries.py    — pure pandas functions (no MCP, no I/O)
├── server.py     — FastMCP wrapper: CSV loading, tool registration, entry point
tests/
├── conftest.py   — sample_df fixture (30-row CSV, same normalization as server)
├── test_queries.py   — 16 unit tests; call queries.py directly, no subprocess
└── natural_disasters_sample.csv
pyproject.toml    — hatchling build; mcp-disaster-server entry point
```

---

## Data Flow

```
uvx launches: mcp-disaster-server (entry point → server.run())
    │
    ├── _ensure_csv(DATA_PATH)
    │     if CSV missing → download from Kaggle via KAGGLE_API_TOKEN
    │     cached at ~/.mcp-disaster-server/natural_disasters.csv
    │
    └── FastMCP stdio loop (stdin/stdout JSON-RPC)
            │
            ├── search_disasters(type, country, year_min, year_max, limit)
            │     → _get_df()  [lazy singleton: read_csv + normalize columns]
            │     → search_disasters_impl(df, ...)   [queries.py]
            │     → str (formatted table or "no results")
            │
            └── get_disaster_statistics(group_by, metric, top_n)
                  → _get_df()
                  → get_disaster_statistics_impl(df, ...)   [queries.py]
                  → str (aggregated table or error message)
```

---

## Key Architectural Decisions

### D-01 · Pure-Function Extraction (queries.py / server.py Split)

**Decision**: All pandas query logic lives in `queries.py` as pure functions that accept
a `pd.DataFrame` and return a `str`. `server.py` is a thin wrapper: it loads the CSV,
maintains the singleton DataFrame, and delegates every tool call to `queries.py`.

**Rationale**: The split enforces a strict boundary between *data logic* and *protocol
logic*. In practice this means:

- **Testability**: `test_queries.py` imports `search_disasters_impl` and
  `get_disaster_statistics_impl` directly, passing a fixture DataFrame. No MCP subprocess
  is started, no CSV is downloaded, no env vars are needed. The test suite runs in any CI
  environment without credentials.
- **Maintainability**: CSV schema changes (new columns, renamed fields) are confined to
  `queries.py`. MCP protocol changes (new transport, tool schema updates) are confined to
  `server.py`. Neither layer needs to know about the other's implementation details.

**Tradeoff**: Two files instead of one. For a package this small, the overhead is trivial
compared to the testability benefit.

→ Satisfies: **ASR-1** (testable without infrastructure)

---

### D-02 · FastMCP stdio Transport with pyproject Entry Point

**Decision**: The server uses `mcp.server.fastmcp.FastMCP` with `transport="stdio"`,
declared as a console script entry point (`mcp-disaster-server`) in `pyproject.toml`.

**Rationale**: `stdio` transport is the standard for locally-launched MCP servers — it
requires no network port, no service discovery, and no authentication layer. The host
process (`uvx`, or a `MultiServerMCPClient`) manages the subprocess lifecycle; the server
simply reads JSON-RPC from stdin and writes to stdout.

`FastMCP` eliminates boilerplate: `@mcp.tool()` decorators generate the tool schema from
the function signature and docstring automatically, keeping the tool contract (names,
argument types, descriptions) co-located with the implementation. The LLM-facing
descriptions live in the docstrings where they are easy to update.

Publishing as a pyproject console script means `uvx --from <git-url> mcp-disaster-server`
installs and runs the server in an isolated temporary environment — no dependency conflicts
with the host agent, no local clone required.

**Tradeoff**: `stdio` transport means the server can only serve one client at a time
(the subprocess model). Acceptable because each MCP host process spawns its own server
subprocess per session.

→ Satisfies: **ASR-2** (deployable without local clone)

---

### D-03 · Lazy Singleton DataFrame with Persistent Kaggle Cache

**Decision**: The CSV is loaded once per process into a module-level `_df` singleton
(`_get_df()`). On first run, if the CSV is absent, the server auto-downloads it from Kaggle
and caches it at `~/.mcp-disaster-server/natural_disasters.csv`. The path can be overridden
via `DISASTER_CSV_PATH` for testing or custom datasets.

**Rationale**: The CSV (~10 MB) is read and column-normalized once at first tool call.
Subsequent calls in the same session pay zero I/O cost. The persistent home-directory cache
survives across `uvx` runs — after the first invocation, the download never repeats. The
`DISASTER_CSV_PATH` env var provides an override that tests and CI can use to point at the
30-row sample fixture without triggering a Kaggle download.

Column normalization (lowercase, underscores, strip punctuation) runs at load time and is
applied uniformly to all query paths — no per-query normalization cost.

**Tradeoff**: The singleton is process-global. A CSV update requires restarting the server
(acceptable for a static historical dataset). The `_ensure_csv` call runs at module import
time in `server.py`, not lazily — meaning a missing CSV without `KAGGLE_API_TOKEN` raises
immediately at startup rather than at first query.

→ Satisfies: **ASR-3** (minimal env contract: only `KAGGLE_API_TOKEN` + `DISASTER_CSV_PATH`)

---

### D-04 · Error-as-String Return Pattern

**Decision**: Both query functions (`search_disasters_impl`, `get_disaster_statistics_impl`)
return `str` in all cases — including invalid-parameter cases. An unknown `group_by` value
returns `"Unknown group_by 'X'. Available: continent, country, ..."` rather than raising a
`ValueError` or `KeyError`.

**Rationale**: The server's consumers are LLM agents in a ReAct loop. When a tool raises
an exception, the MCP host wraps it as a generic error message that may not convey what
went wrong or how to fix it. When a tool returns an informative error string, the LLM reads
it as a `ToolMessage` and can retry with a corrected argument in the next reasoning step.

This pattern matches how the hw-05 agent is configured: `ToolNode(handle_tool_errors=True)`
catches exceptions and converts them to `ToolMessage` objects, but the content is the raw
exception string — less informative than a crafted error message listing valid options.

**Tradeoff**: Callers cannot distinguish "no data found" from "invalid parameter" via return
type alone — both are strings. For a machine-only consumer (the LLM) this is not a problem;
the LLM reads the string content. If a non-LLM caller (e.g., a direct Python test) needs
to distinguish these cases programmatically, it must parse the string.

→ Satisfies: **ASR-4** (informative errors for LLM callers)

---

### D-05 · Test Fixture Mirrors Server Normalization

**Decision**: `tests/conftest.py` applies the identical column normalization transformation
as `server.py::_get_df()` to the sample CSV before exposing it as the `sample_df` fixture.
The normalization logic is intentionally duplicated, not shared via an import from
`server.py`.

**Rationale**: Tests must not depend on `server.py` — importing from `server.py` triggers
`_ensure_csv(DATA_PATH)` at module load time, which would require either a real CSV or
`DISASTER_CSV_PATH` to be set. Duplicating the three-line normalization in `conftest.py`
keeps the test fixture self-contained. If the normalization logic changes in `server.py`,
the test fixture must be updated in sync — an intentional coupling point that is visible
and easy to catch.

**Tradeoff**: Two copies of the normalization transformation exist. Acceptable given the
simplicity of the logic (one list comprehension) and the importance of keeping tests
infrastructure-free.

→ Satisfies: **ASR-1** (tests run without env vars or network access)
