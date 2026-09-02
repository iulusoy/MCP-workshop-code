# MCP Climate Example Repo

This repository contains a small, deterministic example that can be called through an MCP.

## Mock scientific purpose of the example

This is an example that uses mock climate data and aggregates and plots the data. Input: `data/mock_climate.csv` with `date, temperature_c, precipitation_mm, humidity_pct` values per day for one month. 
The output is (1) `outputs/climate_summary.csv` with `month, avg_temperature_c, total_precipitation_mm` for each month. The daily temperature values are aggregated using their mean, while the daily precipitation values are aggregated using their sum; (2) a plot of the data over time.

## Mock user workflow

The user workflow is the following:
1. User obtains `data` from (server, weather station)
2. User prepares the `config` file for the run
3. User executes the script using `data` and `config`
4. User verifies the data by visual inspection of the plot and the summary

This workflow currently requires the user to install the package (hurdle 1), write in a yaml file (hurdle 2), and provide relative paths (hurdle 3). It also requires the user to be in the correct relative directory when running the script (hurdle 4). These hurdles can be circumvented using the functionality through an agent.

Here, an MCP builds the foundation: It defines the API, executes the software, and takes/returns data. It does not explain the workflow or the observations in the data, but serves as the technical interface to the agent - the MCP server wraps the code into a new tool that the agent can call. The implementation is hidden behind a typed interface. Another advantage is portability: An MCP server works on any other MCP-compatible client, and can be available remotely. Using the MCP, the researchers only interact with the scientific workflow ("process climate data") and not the implementation.

## Relevant repo content

- `config/example.yaml`: input parameters for the processing run
- `data/mock_climate.csv`: mock climate time-series data
- `scripts/process_climate.py`: processing and plotting script
- `mcp_server/`: MCP server wrapping the script (see [MCP server](#mcp-server) below)
- `docs/mcp_implementation_plan.md`: implementation plan for the MCP server and its current status
- `outputs/`: generated summary CSV and plot files
- `tests/`: unit tests for the processing/plotting script and the MCP server

## Data processing order in the script

The script does the following in the given order:
1. Parses the command-line arguments giving the relative position of the config file: `parse_args()` 
2. Reads the YAML config file: `load_config()`
3. Loads the mock climate CSV: `run_pipeline()` -> `pd.read_csv()`
4. Cleans and converts the climate data: `prepare_data()`
5. Aggregates the daily data to monthly and saves to `outputs/`: `build_monthly_summary()`
6. Creates and exports a plot of the data: `create_plot()`

## Installing and executing the script

The necessary dependencies can be installed into a Python environment using `pip` or `uv`:
```bash
pip install -r requirements.txt
```

The script is then executed using 
```bash
python scripts/process_climate.py --config config/example.yaml
```

## Expected outputs

The expected outputs are stored in the folder given in the config file, for the default values:
- `outputs/climate_summary.csv`
- `outputs/climate_plot.png`

## Unit tests

Unit tests require installing dev dependencies and can then be run via
```bash
pip install -r requirements-dev.txt
python -m pytest
```

## MCP server

`mcp_server/` wraps the pipeline as an MCP server (`mcp_server/server.py`), so an agent can call it as a tool instead of shelling out to the CLI. It calls `process_climate.run_pipeline()` directly (no subprocess) and reuses `config/schema.json` for validation.

Tools:
- `get_config_schema` — the JSON Schema a config must satisfy (also exposed as the resource `climate://config-schema`)
- `list_sample_data` — CSV files available under `data/`, with their column names
- `validate_climate_config` — validate a config without running the pipeline
- `process_climate_data` — run the pipeline on an inline config; returns a text report (row count, monthly summary table) plus the rendered plot image

Design choices, and the hurdles from the workflow above that they remove:
- **The config is passed inline as JSON**, not as a path to a YAML file the caller has to write and place correctly (hurdles 2-4). Call `get_config_schema` to see the shape, `list_sample_data` to see valid `input_csv` values, and `validate_climate_config` to check a draft before running it.
- **Every path in a config is treated as untrusted input** and resolved by the server (`mcp_server/paths.py`), not trusted verbatim: `input_csv` must resolve inside `data/`, and the `output_path` fields under `plot`/`summary` are reduced to their filename only — the directory portion is discarded. Each call to `process_climate_data` writes to its own fresh directory under `outputs/`, so concurrent or repeated runs never collide or overwrite each other's results, and a config cannot point anywhere else on disk.

### Running the server

```bash
pip install -r requirements.txt   # now includes mcp[cli]
python -m mcp_server.server       # stdio transport
```

or, after `pip install -e .`, via the console script `climate-mcp-server`.

To register it with Claude Code:
```bash
claude mcp add climate-example -- python -m mcp_server.server
```

### Testing

`tests/test_mcp_server.py` calls the tool functions directly (they stay plain, callable Python functions under the `@mcp.tool()` decorator) and covers the sandboxing rules above, including path-traversal attempts in `input_csv` and `output_path`. Run it with the rest of the suite via `python -m pytest`.
