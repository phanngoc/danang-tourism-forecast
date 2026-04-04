"""
Visualization cho dự báo du lịch Đà Nẵng.
Charts đẹp, publication-quality.
"""

import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

from .forecaster import ForecastResult

logger = logging.getLogger(__name__)

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({
    "figure.figsize": (14, 7),
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
})

C_HIST = "#1976D2"
C_FORECAST = "#E64A19"
C_BAND = "#FF7043"
C_EVENT = "#4CAF50"


def plot_trends_forecast(
    history: pd.DataFrame,
    forecast_result: ForecastResult,
    col: str,
    events: Optional[pd.DataFrame] = None,
    last_n: int = 180,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Vẽ Google Trends forecast với confidence bands.

    Args:
        history: DataFrame có DatetimeIndex
        forecast_result: Kết quả forecast
        col: Tên cột trong history
        events: DataFrame events (optional, để đánh dấu)
        last_n: Hiển thị N ngày cuối
        save_path: Đường dẫn lưu

    Returns:
        Figure
    """
    fig, ax = plt.subplots(figsize=(15, 7))

    # History
    hist = history.tail(last_n)
    ax.plot(hist.index, hist[col], color=C_HIST, linewidth=1.5, label="Thực tế")

    # Forecast dates
    last_date = hist.index[-1]
    freq = pd.infer_freq(hist.index) or "D"
    if "W" in str(freq):
        forecast_dates = pd.date_range(last_date + pd.Timedelta(weeks=1),
                                       periods=forecast_result.horizon, freq="W")
    else:
        forecast_dates = pd.bdate_range(last_date + pd.Timedelta(days=1),
                                        periods=forecast_result.horizon)

    n = min(len(forecast_dates), forecast_result.horizon)
    fd = forecast_dates[:n]
    point = forecast_result.point_forecast[:n]

    # Forecast line
    ax.plot(fd, point, color=C_FORECAST, linewidth=2, linestyle="--", label="Du bao")

    # Confidence bands
    q = forecast_result.quantile_forecast[:n]
    if q.shape[1] >= 10:
        ax.fill_between(fd, q[:, 1], q[:, -1], alpha=0.12, color=C_BAND, label="10%-90%")
        ax.fill_between(fd, q[:, 2], q[:, -2], alpha=0.18, color=C_BAND, label="20%-80%")
        ax.fill_between(fd, q[:, 3], q[:, -3], alpha=0.25, color=C_BAND, label="30%-70%")

    # Connect
    ax.plot([hist.index[-1], fd[0]], [hist[col].iloc[-1], point[0]],
            color=C_FORECAST, linewidth=1, linestyle=":")

    # Events markers
    if events is not None:
        evt = events[events["has_event"] == 1]
        evt_in_range = evt[(evt.index >= hist.index[0]) & (evt.index <= fd[-1])]
        for date in evt_in_range.index:
            ax.axvline(x=date, color=C_EVENT, alpha=0.3, linestyle="--", linewidth=0.8)

    # Format
    trend_pct = forecast_result.trend_pct
    arrow = "Tang" if trend_pct > 0 else "Giam"
    title = f"Du bao Du lich Da Nang — {forecast_result.name}"
    subtitle = f"Forecast {forecast_result.horizon} buoc | Xu huong: {arrow} {abs(trend_pct):.1f}%"
    ax.set_title(f"{title}\n{subtitle}", fontweight="bold", pad=15)
    ax.set_xlabel("Ngay")
    ax.set_ylabel("Search Interest / Gia tri")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Chart saved: {save_path}")

    return fig


def plot_monthly_visitors_forecast(
    visitors: pd.DataFrame,
    forecast_result: ForecastResult,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Vẽ forecast lượng khách hàng tháng.
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    # History bars
    x_hist = range(len(visitors))
    bars = ax.bar(x_hist, visitors["total_visitors_k"],
                  color=C_HIST, alpha=0.7, label="Thuc te (nghin luot)")

    # Stack intl vs domestic
    ax.bar(x_hist, visitors["intl_visitors_k"],
           color="#FF9800", alpha=0.8, label="Quoc te")

    # Forecast
    n_fc = forecast_result.horizon
    x_fc = range(len(visitors), len(visitors) + n_fc)
    ax.bar(x_fc, forecast_result.point_forecast[:n_fc],
           color=C_FORECAST, alpha=0.6, label="Du bao")

    # Error bars (quantiles)
    q = forecast_result.quantile_forecast[:n_fc]
    if q.shape[1] >= 10:
        lower = forecast_result.point_forecast[:n_fc] - q[:, 1]
        upper = q[:, -1] - forecast_result.point_forecast[:n_fc]
        ax.errorbar(x_fc, forecast_result.point_forecast[:n_fc],
                    yerr=[lower, upper], fmt="none", color="red", alpha=0.5, capsize=3)

    # Labels
    all_dates = list(visitors.index.strftime("%m/%y"))
    last_date = visitors.index[-1]
    for i in range(n_fc):
        next_month = last_date + pd.DateOffset(months=i + 1)
        all_dates.append(next_month.strftime("%m/%y"))

    step = max(1, len(all_dates) // 20)
    ax.set_xticks(range(0, len(all_dates), step))
    ax.set_xticklabels([all_dates[i] for i in range(0, len(all_dates), step)], rotation=45)

    ax.set_title("Luong khach du lich Da Nang — Thuc te vs Du bao",
                 fontweight="bold", pad=15)
    ax.set_ylabel("Nghin luot khach")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Chart saved: {save_path}")

    return fig


def plot_dashboard(
    trends_results: dict[str, ForecastResult],
    visitor_result: Optional[ForecastResult] = None,
    weather: Optional[pd.DataFrame] = None,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Dashboard tổng hợp: nhiều metrics trên 1 figure.
    """
    n_panels = len(trends_results) + (1 if visitor_result else 0) + (1 if weather is not None else 0)
    cols = min(n_panels, 2)
    rows = (n_panels + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(8 * cols, 5 * rows))
    if n_panels == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    idx = 0

    # Trends panels
    for name, result in trends_results.items():
        ax = axes[idx]
        point = result.point_forecast
        ax.plot(point, color=C_FORECAST, linewidth=2)
        if result.quantile_forecast.shape[1] >= 10:
            q = result.quantile_forecast
            ax.fill_between(range(len(point)), q[:, 2], q[:, -2],
                           alpha=0.2, color=C_BAND)
        trend = result.trend_pct
        arrow = "+" if trend > 0 else ""
        ax.set_title(f"{name} ({arrow}{trend:.1f}%)", fontweight="bold")
        ax.grid(True, alpha=0.3)
        idx += 1

    # Visitors panel
    if visitor_result:
        ax = axes[idx]
        ax.bar(range(visitor_result.horizon), visitor_result.point_forecast,
               color=C_FORECAST, alpha=0.7)
        ax.set_title(f"Khach du bao ({visitor_result.trend_pct:+.1f}%)", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        idx += 1

    # Weather panel
    if weather is not None:
        ax = axes[idx]
        recent = weather.tail(90)
        ax.plot(recent.index, recent["temp_max"], color="red", alpha=0.7, label="Nhiet do max")
        ax2 = ax.twinx()
        ax2.bar(recent.index, recent["rain"], color="blue", alpha=0.3, label="Mua (mm)")
        ax.set_title("Thoi tiet Da Nang (90 ngay)", fontweight="bold")
        ax.legend(loc="upper left")
        ax2.legend(loc="upper right")
        idx += 1

    # Hide unused
    for j in range(idx, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("DASHBOARD DU BAO DU LICH DA NANG",
                 fontsize=18, fontweight="bold", y=1.02)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Dashboard saved: {save_path}")

    return fig
