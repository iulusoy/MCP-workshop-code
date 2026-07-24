# MCP Climate Example Repo

This repository is a small, deterministic example that can be called from an MCP tool or used as a local demo.

## Contents

- `config/example.yaml`: input parameters for the processing run
- `data/mock_climate.csv`: mock climate time-series data
- `scripts/process_climate.py`: processing and plotting script
- `outputs/`: generated summary CSV and plot files

## What the script does

1. Reads the YAML config file
2. Loads the mock climate CSV
3. Cleans and converts the climate data
4. Computes a rolling temperature mean and a monthly summary
5. Saves a plot and a summary CSV to `outputs/`

## Run it

```bash
python scripts/process_climate.py --config config/example.yaml
```

## Expected outputs

- `outputs/climate_summary.csv`
- `outputs/climate_plot.png`

## Notes for MCP use

The script is designed to be non-interactive and deterministic, so an MCP server can invoke it directly with the config path and inspect the generated files afterward.
