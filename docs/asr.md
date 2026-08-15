# Architecturally Significant Requirements — mcp-disaster-server

## Overview

This package is a focused utility: a single-purpose MCP server exposing natural disaster
data from the Kaggle EOSDIS dataset (1900–2021) over the stdio protocol. The four ASRs
below are the requirements that shaped its internal structure and deployment contract.

---

## ASR Catalog

### ASR-1 · Query Logic Testable Without Infrastructure

| Attribute | Value |
|-----------|-------|
| **Category** | Maintainability / Testability |
| **Priority** | High |
| **Source** | hw-05 course requirement: "test coverage is mandatory" |

**Requirement**: The pandas filter and aggregation logic must be unit-testable without
starting an MCP subprocess, downloading the Kaggle CSV, or requiring any API credentials.

**Architectural impact**: Query logic is extracted into `mcp_disaster/queries.py` as two
pure functions (`search_disasters_impl`, `get_disaster_statistics_impl`). `mcp_disaster/server.py`
is a thin wrapper that loads the DataFrame and delegates to these functions. Tests import
and call the pure functions directly with a 30-row sample CSV fixture — no network, no
subprocess, no credentials.

→ Decision: **D-01** (pure-function extraction), **D-05** (test fixture pattern)

---

### ASR-2 · Deployable Without a Local Clone

| Attribute | Value |
|-----------|-------|
| **Category** | Operability |
| **Priority** | High |
| **Source** | MCP ecosystem standard; hw-05 integration contract |

**Requirement**: Any MCP host (hw-05 or otherwise) must be able to launch this server
without checking out the repository locally — via `uvx --from <git-url> mcp-disaster-server`
or a standard pip install.

**Architectural impact**: The package uses `pyproject.toml` with a `[project.scripts]`
entry point. `hatchling` builds a proper wheel. The entry point `mcp-disaster-server`
calls `mcp_disaster.server:run`, which starts the `FastMCP` stdio loop. No path manipulation,
no `python -m` invocation — just a named console script that `uvx` can execute in an
isolated environment.

→ Decision: **D-02** (FastMCP stdio transport + pyproject entry point)

---

### ASR-3 · Minimal Environment Contract

| Attribute | Value |
|-----------|-------|
| **Category** | Security |
| **Priority** | High |
| **Source** | hw-05 D-02 (minimal env passthrough to subprocesses) |

**Requirement**: The server must function correctly when launched with only its own required
env vars in scope (`KAGGLE_API_TOKEN`, `DISASTER_CSV_PATH`). It must not assume access to
the parent agent's full environment.

**Architectural impact**: The server reads only two env vars: `DISASTER_CSV_PATH` (optional
override for the CSV path) and `KAGGLE_API_TOKEN` (required only for first-run download).
No other env vars are accessed. This makes the minimal-env passthrough in hw-05's
`_base_env()` sufficient and auditable.

→ Decision: **D-03** (lazy Kaggle download + path override)

---

### ASR-4 · Informative Error Responses (Not Exceptions)

| Attribute | Value |
|-----------|-------|
| **Category** | Reliability |
| **Priority** | Medium |
| **Source** | MCP tool design: the LLM caller must be able to reason about errors |

**Requirement**: When a tool is called with an invalid parameter (unknown `group_by`,
unknown `metric`), the server must return a human-readable string describing what went
wrong and what the valid options are — not raise an exception that crashes the MCP session.

**Architectural impact**: `search_disasters_impl` and `get_disaster_statistics_impl` return
`str` in all cases — including error cases. Invalid parameters produce messages like
`"Unknown group_by 'bad_column'. Available: continent, country, ..."`. The LLM receives
this as a `ToolMessage` and can retry with a corrected argument, matching the ReAct error
recovery pattern in hw-05 (`ToolNode(handle_tool_errors=True)`).

→ Decision: **D-04** (error-as-string return pattern)

---

## Priority Summary

| ID | Category | Priority | Requirement |
|----|----------|----------|-------------|
| ASR-1 | Maintainability | High | Query logic testable without MCP subprocess or credentials |
| ASR-2 | Operability | High | Launchable via `uvx` without a local repository clone |
| ASR-3 | Security | High | Works with minimal env passthrough (no full `os.environ`) |
| ASR-4 | Reliability | Medium | Invalid parameters return error strings, not exceptions |
