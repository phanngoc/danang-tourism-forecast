#!/usr/bin/env python3
"""
Benchmark: So sanh TimesFM 2.5 vs cac model truyen thong.
Supports any Vietnamese city via --city flag.

Models:
  1. Naive (Last Value)
  2. Seasonal Naive
  3. Moving Average
  4. Holt-Winters (Exponential Smoothing)
  5. Auto-ARIMA
  6. Prophet (Meta)
  7. TimesFM 2.5 (Google Research)

Usage:
    python benchmark.py                        # Da Nang (default)
    python benchmark.py --city hue             # Hue
    python benchmark.py --city hue --series visitors
    python benchmark.py --city danang --series trends
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent))

from src.city_config import load_all_cities, get_city, list_cities
from src.data_collector import collect_all, get_visitor_data
from src.forecaster import TourismForecaster
from src.baselines import run_all_baselines, evaluate_all, BaselineForecast

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

sns.set_theme(style="whitegrid")


def benchmark_walk_forward(
    series: np.ndarray,
    horizon: int,
    n_splits: int = 3,
    step: int = None,
    seasonal_periods: int = 12,
    dates: pd.DatetimeIndex = None,
    freq: str = "MS",
    forecaster: TourismForecaster = None,
) -> pd.DataFrame:
    """
    Walk-forward benchmark cho tat ca models.
    Chia data thanh n_splits, moi split forecast horizon buoc roi so sanh.
    """
    if step is None:
        step = horizon

    n = len(series)
    min_train = n - (n_splits * step + horizon)
    if min_train < seasonal_periods * 2:
        min_train = seasonal_periods * 2

    all_results = []
    split_idx = 0
    train_end = min_train

    while train_end + horizon <= n and split_idx < n_splits:
        train = series[:train_end]
        actual = series[train_end:train_end + horizon]
        h = len(actual)

        train_dates = dates[:train_end] if dates is not None else None

        logger.info(f"\n--- Split {split_idx + 1}/{n_splits} (train={train_end}, test={h}) ---")

        # Baselines
        logger.info("Running baselines...")
        baselines = run_all_baselines(train, h, seasonal_periods, train_dates, freq)

        # TimesFM
        if forecaster is not None:
            logger.info("  Running TimesFM 2.5...")
            t0 = time.time()
            tfm_result = forecaster.forecast(train, horizon=h, name="TimesFM 2.5")
            tfm_time = (time.time() - t0) * 1000
            baselines.append(BaselineForecast(
                name="TimesFM 2.5",
                point_forecast=tfm_result.point_forecast,
                horizon=h,
                train_time_ms=tfm_time,
            ))
            logger.info(f"  TimesFM 2.5 done")

        # Evaluate
        metrics = evaluate_all(train, baselines, actual)
        metrics["split"] = split_idx
        all_results.append(metrics)

        train_end += step
        split_idx += 1

    # Average across splits
    combined = pd.concat(all_results)
    avg = combined.groupby("Model").agg({
        "MAE": "mean",
        "RMSE": "mean",
        "MAPE (%)": "mean",
        "Dir Acc (%)": "mean",
        "Train (ms)": "mean",
    }).round(2).sort_values("MAE")

    return avg, combined


def plot_benchmark(
    avg_metrics: pd.DataFrame,
    title: str = "Benchmark",
    save_path: str = None,
) -> plt.Figure:
    """Ve benchmark comparison chart."""
    fig, axes = plt.subplots(1, 4, figsize=(20, 6))

    metrics = ["MAE", "RMSE", "MAPE (%)", "Dir Acc (%)"]
    colors_map = {
        "TimesFM 2.5": "#E64A19",
        "Prophet": "#1976D2",
        "Auto-ARIMA": "#388E3C",
        "Holt-Winters": "#7B1FA2",
        "Seasonal Naive": "#F57C00",
        "Moving Average": "#0097A7",
        "Naive (Last Value)": "#757575",
    }

    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        models = avg_metrics.index.tolist()
        values = avg_metrics[metric].values

        colors = [colors_map.get(m, "#9E9E9E") for m in models]

        # Highlight TimesFM
        bars = ax.barh(models, values, color=colors, alpha=0.85)
        for i, m in enumerate(models):
            if "TimesFM" in m:
                bars[i].set_edgecolor("red")
                bars[i].set_linewidth(2)

        ax.set_title(metric, fontweight="bold", fontsize=12)
        ax.grid(True, alpha=0.3, axis="x")

        # Value labels
        for i, v in enumerate(values):
            ax.text(v + max(values) * 0.02, i, f"{v:.1f}", va="center", fontsize=9)

    fig.suptitle(f"Benchmark: {title}", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Chart saved: {save_path}")

    return fig


def plot_forecast_comparison(
    series: np.ndarray,
    actual: np.ndarray,
    forecasts: list,
    tfm_forecast: np.ndarray,
    title: str = "",
    save_path: str = None,
) -> plt.Figure:
    """Ve so sanh forecast cua cac models."""
    fig, ax = plt.subplots(figsize=(15, 7))

    # Context (last 20 points)
    ctx = min(20, len(series))
    x_ctx = range(ctx)
    ax.plot(x_ctx, series[-ctx:], color="black", linewidth=2, label="History", marker="o", markersize=3)

    # Actual
    x_fc = range(ctx, ctx + len(actual))
    ax.plot(x_fc, actual, color="black", linewidth=2, linestyle="--", label="Actual", marker="s", markersize=4)

    # Models
    colors = ["#1976D2", "#388E3C", "#7B1FA2", "#F57C00", "#0097A7", "#757575"]
    for i, fc in enumerate(forecasts):
        pred = fc.point_forecast[:len(actual)]
        c = colors[i % len(colors)]
        ax.plot(x_fc[:len(pred)], pred, linewidth=1.2, alpha=0.7, label=fc.name, color=c)

    # TimesFM (highlighted)
    ax.plot(x_fc[:len(tfm_forecast)], tfm_forecast[:len(actual)],
            color="#E64A19", linewidth=2.5, label="TimesFM 2.5", marker="D", markersize=4)

    ax.axvline(x=ctx - 0.5, color="gray", linestyle=":", alpha=0.5)
    ax.set_title(f"So sanh Forecast: {title}", fontweight="bold", fontsize=14)
    ax.set_ylabel("Gia tri")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def main():
    load_all_cities()

    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="danang",
                        help=f"City ID (available: {', '.join(list_cities())})")
    parser.add_argument("--series", default="all", choices=["all", "visitors", "trends"])
    parser.add_argument("--horizon", type=int, default=6)
    parser.add_argument("--splits", type=int, default=3)
    args = parser.parse_args()

    city = get_city(args.city)
    out = Path(f"output/benchmark/{city.city_id}")
    out.mkdir(parents=True, exist_ok=True)

    # Collect data
    logger.info("=" * 60)
    logger.info(f"COLLECTING DATA — {city.city_name}")
    logger.info("=" * 60)
    data = collect_all(
        city=city,
        start_date="2023-01-01",
        fetch_trends=(args.series in ["all", "trends"]),
    )

    # Load TimesFM
    logger.info("\nLOADING TimesFM 2.5...")
    forecaster = TourismForecaster(max_context=512, max_horizon=128)
    forecaster.load_model()

    all_benchmarks = {}

    # BENCHMARK VISITORS
    if args.series in ["all", "visitors"]:
        logger.info("\n" + "=" * 60)
        logger.info(f"BENCHMARK: Luong khach — {city.city_name}")
        logger.info("=" * 60)

        visitors = data["visitors"]
        v_series = visitors["total_visitors_k"].values.astype(float)

        avg, detailed = benchmark_walk_forward(
            v_series,
            horizon=args.horizon,
            n_splits=args.splits,
            seasonal_periods=12,
            dates=visitors.index,
            freq="MS",
            forecaster=forecaster,
        )

        print("\n" + "=" * 60)
        print(f"VISITORS BENCHMARK RESULTS — {city.city_name}")
        print("=" * 60)
        print(avg.to_string())

        plot_benchmark(avg, f"Luong khach Du lich {city.city_name} (monthly)",
                      save_path=str(out / "benchmark_visitors.png"))

        avg.to_csv(out / "benchmark_visitors.csv")
        all_benchmarks["visitors"] = avg

    # BENCHMARK TRENDS
    if args.series in ["all", "trends"] and "trends_weekly" in data:
        logger.info("\n" + "=" * 60)
        logger.info(f"BENCHMARK: Google Trends (weekly) — {city.city_name}")
        logger.info("=" * 60)

        trends = data["trends_weekly"]
        # Pick first 3 tourism queries
        test_queries = list(city.tourism_queries.keys())[:3]
        test_queries = [q for q in test_queries if q in trends.columns]

        for query in test_queries:
            logger.info(f"\n--- {query} ---")
            t_series = trends[query].dropna().values.astype(float)

            if len(t_series) < 30:
                logger.warning(f"Skip {query}: too short ({len(t_series)})")
                continue

            avg, detailed = benchmark_walk_forward(
                t_series,
                horizon=args.horizon,
                n_splits=args.splits,
                seasonal_periods=52,
                freq="W",
                forecaster=forecaster,
            )

            print(f"\n{'=' * 60}")
            print(f"TRENDS BENCHMARK: {query} — {city.city_name}")
            print("=" * 60)
            print(avg.to_string())

            plot_benchmark(avg, f"Google Trends: {query} ({city.city_name})",
                          save_path=str(out / f"benchmark_{query}.png"))
            avg.to_csv(out / f"benchmark_{query}.csv")
            all_benchmarks[query] = avg

    # FINAL SUMMARY
    print("\n" + "=" * 60)
    print(f"FINAL SUMMARY — {city.city_name}")
    print("=" * 60)
    for name, metrics in all_benchmarks.items():
        print(f"\n--- {name} ---")
        if "TimesFM 2.5" in metrics.index:
            rank = list(metrics.index).index("TimesFM 2.5") + 1
            total = len(metrics)
            tfm_mae = metrics.loc["TimesFM 2.5", "MAE"]
            best_mae = metrics["MAE"].iloc[0]
            best_model = metrics.index[0]
            print(f"  TimesFM 2.5: Rank {rank}/{total} (MAE={tfm_mae})")
            print(f"  Best model:  {best_model} (MAE={best_mae})")
            if rank == 1:
                print(f"  TimesFM 2.5 WINS!")
            else:
                gap = (tfm_mae - best_mae) / best_mae * 100
                print(f"  Gap: {gap:+.1f}% vs best")

    logger.info(f"\nAll results saved to: {out}/")


if __name__ == "__main__":
    main()
