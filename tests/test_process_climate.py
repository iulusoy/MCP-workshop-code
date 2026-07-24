from pathlib import Path

import pandas as pd
import pytest
import yaml

import process_climate as pc

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_resolve_path_absolute():
    absolute = Path("/tmp/some/file.csv")
    assert pc.resolve_path(Path("/whatever"), str(absolute)) == absolute


def test_resolve_path_relative(tmp_path):
    result = pc.resolve_path(tmp_path, "sub/file.csv")
    assert result == (tmp_path / "sub/file.csv").resolve()


def test_prepare_data_interpolates_and_fills():
    frame = pd.DataFrame(
        {
            "date": ["2026-01-03", "2026-01-01", "2026-01-02"],
            "temp": [None, 1.0, 3.0],
            "precip": [2.0, None, 1.0],
        }
    )

    processed = pc.prepare_data(frame, "date", "temp", "precip", rolling_window_days=2)

    assert list(processed.index) == list(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]))
    assert processed["temp"].isna().sum() == 0
    assert processed.loc[pd.Timestamp("2026-01-03"), "temp"] == pytest.approx(3.0)
    assert processed["precip"].isna().sum() == 0
    assert processed.loc[pd.Timestamp("2026-01-01"), "precip"] == pytest.approx(0.0)
    assert "temp_rolling_mean" in processed.columns
    assert "precip_rolling_sum" in processed.columns


def test_build_monthly_summary():
    index = pd.to_datetime(["2026-01-01", "2026-01-15", "2026-02-01"])
    frame = pd.DataFrame({"temp": [0.0, 10.0, 100.0], "precip": [1.0, 3.0, 5.0]}, index=index)

    monthly = pc.build_monthly_summary(frame, "temp", "precip")

    jan = monthly[monthly["month"] == pd.Timestamp("2026-01-01")].iloc[0]
    feb = monthly[monthly["month"] == pd.Timestamp("2026-02-01")].iloc[0]
    assert jan["avg_temperature_c"] == pytest.approx(5.0)
    assert jan["total_precipitation_mm"] == pytest.approx(4.0)
    assert feb["avg_temperature_c"] == pytest.approx(100.0)
    assert feb["total_precipitation_mm"] == pytest.approx(5.0)


def _valid_config_dict(input_csv="data.csv", plot_path="out/plot.png", summary_path="out/summary.csv"):
    return {
        "input_csv": input_csv,
        "date_column": "date",
        "metrics": {"temperature_c": "temperature_c", "precipitation_mm": "precipitation_mm"},
        "rolling_window_days": 3,
        "plot": {"title": "Test", "output_path": plot_path, "width": 6, "height": 4},
        "summary": {"output_path": summary_path},
    }


def test_load_config_valid_repo_example():
    config = pc.load_config(REPO_ROOT / "config" / "example.yaml")
    assert config["date_column"] == "date"
    assert config["metrics"]["temperature_c"] == "temperature_c"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.pop("date_column"),
        lambda c: c.update(unexpected_field="surprise"),
        lambda c: c.update(rolling_window_days=0),
    ],
    ids=["missing-required-field", "unknown-field", "bad-rolling-window-days"],
)
def test_load_config_rejects_invalid_config(tmp_path, mutate):
    config = _valid_config_dict()
    mutate(config)
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(yaml.safe_dump(config))

    with pytest.raises(ValueError):
        pc.load_config(config_path)


def test_run_pipeline_end_to_end(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_path = data_dir / "mini_climate.csv"
    csv_path.write_text(
        "date,temperature_c,precipitation_mm\n"
        "2026-01-01,1.0,0.0\n"
        "2026-01-02,2.0,1.0\n"
        "2026-01-03,3.0,0.0\n"
        "2026-02-01,4.0,2.0\n"
    )

    config = _valid_config_dict(
        input_csv="data/mini_climate.csv",
        plot_path="outputs/plot.png",
        summary_path="outputs/summary.csv",
    )

    result = pc.run_pipeline(config, tmp_path)

    summary_path = Path(result["summary_path"])
    plot_path = Path(result["plot_path"])
    assert summary_path.exists()
    assert plot_path.exists()
    assert plot_path.stat().st_size > 0
    assert result["rows_processed"] == 4

    summary = pd.read_csv(summary_path)
    assert list(summary["month"]) == ["2026-01-01", "2026-02-01"]
    assert summary.loc[0, "avg_temperature_c"] == pytest.approx(2.0)
    assert summary.loc[1, "avg_temperature_c"] == pytest.approx(4.0)


def test_run_from_config_path_matches_repo_example():
    result = pc.run_from_config_path(REPO_ROOT / "config" / "example.yaml")

    assert Path(result["summary_path"]).exists()
    assert Path(result["plot_path"]).exists()
    assert result["rows_processed"] > 0
