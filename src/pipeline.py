"""
End-to-end pipeline: collect → forecast → visualize → report.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .data_collector import (
    collect_all, get_visitor_data, get_event_series,
    TOURISM_QUERIES, INTL_QUERIES,
)
from .forecaster import TourismForecaster, ForecastResult
from .visualizer import (
    plot_trends_forecast,
    plot_monthly_visitors_forecast,
    plot_dashboard,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Tất cả kết quả pipeline."""
    trends_forecasts: dict[str, ForecastResult]
    visitor_forecast: Optional[ForecastResult]
    data: dict[str, pd.DataFrame]
    output_dir: str = "output"

    def summary_text(self) -> str:
        """Tạo text summary cho Telegram/bot."""
        lines = [
            "=== DU BAO DU LICH DA NANG ===",
            "",
        ]

        # Trends
        lines.append("--- Google Trends (xu huong tim kiem) ---")
        for name, r in self.trends_forecasts.items():
            trend = r.trend_pct
            arrow = "Tang" if trend > 0 else "Giam"
            lines.append(f"  {name}: {arrow} {abs(trend):.1f}% trong {r.horizon} buoc")

        # Visitors
        if self.visitor_forecast:
            r = self.visitor_forecast
            last = r.last_value
            pred = r.point_forecast[-1]
            lines.extend([
                "",
                "--- Luong khach du bao ---",
                f"  Thang gan nhat: {last:,.0f}K luot",
                f"  Du bao thang +{r.horizon}: {pred:,.0f}K luot ({r.trend_pct:+.1f}%)",
                f"  Khoang: {r.lower_10[-1]:,.0f}K — {r.upper_90[-1]:,.0f}K",
            ])

        # Interpretation
        avg_trend = np.mean([r.trend_pct for r in self.trends_forecasts.values()])
        lines.extend([
            "",
            "--- Nhan dinh ---",
        ])
        if avg_trend > 5:
            lines.append("  Du lich TANG MANH — nen tang gia phong, tuyen them nhan vien")
        elif avg_trend > 0:
            lines.append("  Du lich TANG NHE — duy tri hoat dong binh thuong")
        elif avg_trend > -5:
            lines.append("  Du lich GIAM NHE — can than voi ton kho")
        else:
            lines.append("  Du lich GIAM MANH — giam chi phi, khuyen mai de kich cau")

        return "\n".join(lines)

    def export(self, path: Optional[str] = None):
        """Xuất CSV + charts."""
        base = Path(path or self.output_dir)
        base.mkdir(parents=True, exist_ok=True)

        # CSV forecasts
        for name, r in self.trends_forecasts.items():
            df = pd.DataFrame({
                "step": range(1, r.horizon + 1),
                "point": r.point_forecast,
                "lower_10": r.lower_10,
                "upper_90": r.upper_90,
            })
            safe_name = name.replace(" ", "_").lower()
            df.to_csv(base / f"forecast_{safe_name}.csv", index=False)

        if self.visitor_forecast:
            r = self.visitor_forecast
            df = pd.DataFrame({
                "month": range(1, r.horizon + 1),
                "visitors_k": r.point_forecast,
                "lower_10": r.lower_10,
                "upper_90": r.upper_90,
            })
            df.to_csv(base / f"forecast_visitors.csv", index=False)

        logger.info(f"Exported to {base}")


class DanangTourismPipeline:
    """
    Pipeline chính.

    Usage:
        pipeline = DanangTourismPipeline()
        result = pipeline.run()
        print(result.summary_text())
        result.export("output")
    """

    def __init__(
        self,
        start_date: str = "2023-01-01",
        trends_horizon: int = 12,  # 12 weeks
        visitor_horizon: int = 6,  # 6 months
        output_dir: str = "output",
        fetch_trends: bool = True,
    ):
        self.start_date = start_date
        self.trends_horizon = trends_horizon
        self.visitor_horizon = visitor_horizon
        self.output_dir = output_dir
        self.fetch_trends = fetch_trends
        self.forecaster = TourismForecaster(max_context=512, max_horizon=128)

    def run(self) -> PipelineResult:
        """Chạy toàn bộ pipeline."""

        # 1. Collect data
        logger.info("=" * 60)
        logger.info("STEP 1: Thu thap du lieu")
        logger.info("=" * 60)
        data = collect_all(
            start_date=self.start_date,
            fetch_trends=self.fetch_trends,
        )

        # 2. Load model
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Load TimesFM 2.5")
        logger.info("=" * 60)
        self.forecaster.load_model()

        # 3. Forecast Google Trends
        trends_forecasts = {}
        if "trends_weekly" in data:
            logger.info("\n" + "=" * 60)
            logger.info("STEP 3: Forecast Google Trends")
            logger.info("=" * 60)

            trends_df = data["trends_weekly"]
            series_dict = {}
            for col in trends_df.columns:
                s = trends_df[col].dropna().values
                if len(s) > 20:
                    series_dict[col] = s

            if series_dict:
                trends_forecasts = self.forecaster.forecast_multiple(
                    series_dict, horizon=self.trends_horizon
                )
                for name, r in trends_forecasts.items():
                    logger.info(f"  {name}: {r.trend_pct:+.1f}%")

        # 4. Forecast visitors
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Forecast luong khach hang thang")
        logger.info("=" * 60)

        visitors = data["visitors"]
        visitor_series = visitors["total_visitors_k"].values
        visitor_forecast = self.forecaster.forecast(
            visitor_series,
            horizon=self.visitor_horizon,
            name="Khach du lich Da Nang",
        )
        logger.info(
            f"  Last: {visitor_forecast.last_value:,.0f}K | "
            f"Forecast +{self.visitor_horizon}m: "
            f"{visitor_forecast.point_forecast[-1]:,.0f}K "
            f"({visitor_forecast.trend_pct:+.1f}%)"
        )

        # 5. Visualize
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: Generate charts")
        logger.info("=" * 60)

        out = Path(self.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        events = data.get("events")

        # Trends charts
        if "trends_weekly" in data and trends_forecasts:
            for col, result in trends_forecasts.items():
                plot_trends_forecast(
                    data["trends_weekly"], result, col,
                    events=events,
                    save_path=str(out / f"forecast_{col}.png"),
                )

        # Visitors chart
        plot_monthly_visitors_forecast(
            visitors, visitor_forecast,
            save_path=str(out / "forecast_visitors.png"),
        )

        # Dashboard
        plot_dashboard(
            trends_forecasts,
            visitor_forecast,
            weather=data.get("weather"),
            save_path=str(out / "dashboard.png"),
        )

        result = PipelineResult(
            trends_forecasts=trends_forecasts,
            visitor_forecast=visitor_forecast,
            data=data,
            output_dir=self.output_dir,
        )

        # Summary
        logger.info("\n" + result.summary_text())
        result.export()

        return result
