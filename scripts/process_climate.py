from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import yaml


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base_dir / path).resolve()


def prepare_data(frame: pd.DataFrame, date_column: str, temp_column: str, precip_column: str, rolling_window_days: int) -> pd.DataFrame:
    processed = frame.copy()
    processed[date_column] = pd.to_datetime(processed[date_column], errors="raise")
    processed[temp_column] = pd.to_numeric(processed[temp_column], errors="coerce")
    processed[precip_column] = pd.to_numeric(processed[precip_column], errors="coerce")
    processed = processed.sort_values(date_column).set_index(date_column)
    processed[temp_column] = processed[temp_column].interpolate(limit_direction="both")
    processed[precip_column] = processed[precip_column].fillna(0)
    processed[f"{temp_column}_rolling_mean"] = processed[temp_column].rolling(rolling_window_days, min_periods=1).mean()
    processed[f"{precip_column}_rolling_sum"] = processed[precip_column].rolling(rolling_window_days, min_periods=1).sum()
    return processed


def build_monthly_summary(frame: pd.DataFrame, temp_column: str, precip_column: str) -> pd.DataFrame:
    monthly = frame.resample("MS").agg({
        temp_column: "mean",
        precip_column: "sum",
    })
    monthly = monthly.rename(columns={
        temp_column: "avg_temperature_c",
        precip_column: "total_precipitation_mm",
    })
    monthly.index.name = "month"
    return monthly.reset_index()


def create_plot(frame: pd.DataFrame, temp_column: str, precip_column: str, output_path: Path, title: str, width: float, height: float) -> None:
    fig, ax_temp = plt.subplots(figsize=(width, height))
    ax_precip = ax_temp.twinx()

    ax_temp.plot(frame.index, frame[temp_column], color="#2A6FDB", linewidth=1.8, label="Temperature (C)")
    ax_temp.plot(frame.index, frame[f"{temp_column}_rolling_mean"], color="#0B3A67", linewidth=2.5, linestyle="--", label="Rolling mean")
    ax_precip.bar(frame.index, frame[precip_column], color="#5CA9E6", alpha=0.25, width=0.8, label="Precipitation (mm)")

    ax_temp.set_title(title)
    ax_temp.set_xlabel("Date")
    ax_temp.set_ylabel("Temperature (C)")
    ax_precip.set_ylabel("Precipitation (mm)")
    ax_temp.grid(True, axis="y", alpha=0.25)

    handles_temp, labels_temp = ax_temp.get_legend_handles_labels()
    handles_precip, labels_precip = ax_precip.get_legend_handles_labels()
    ax_temp.legend(handles_temp + handles_precip, labels_temp + labels_precip, loc="upper right")

    fig.autofmt_xdate()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process mock climate data from a YAML config file.")
    parser.add_argument("--config", required=True, help="Path to the YAML configuration file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_root = config_path.parent.parent

    input_csv = resolve_path(project_root, config["input_csv"])
    date_column = config["date_column"]
    temp_column = config["metrics"]["temperature_c"]
    precip_column = config["metrics"]["precipitation_mm"]
    rolling_window_days = int(config.get("rolling_window_days", 7))

    plot_config = config["plot"]
    summary_config = config["summary"]
    plot_output = resolve_path(project_root, plot_config["output_path"])
    summary_output = resolve_path(project_root, summary_config["output_path"])

    frame = pd.read_csv(input_csv)
    processed = prepare_data(frame, date_column, temp_column, precip_column, rolling_window_days)
    monthly_summary = build_monthly_summary(processed, temp_column, precip_column)

    summary_output.parent.mkdir(parents=True, exist_ok=True)
    monthly_summary.to_csv(summary_output, index=False)

    create_plot(
        processed,
        temp_column,
        precip_column,
        plot_output,
        plot_config.get("title", "Climate Trends"),
        float(plot_config.get("width", 12)),
        float(plot_config.get("height", 7)),
    )

    print(f"Read data from: {input_csv}")
    print(f"Wrote summary to: {summary_output}")
    print(f"Wrote plot to: {plot_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
