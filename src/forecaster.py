"""
Forecaster: dùng TimesFM 2.5 để dự báo du lịch Đà Nẵng.

Hỗ trợ:
- Forecast Google Trends (daily/weekly) → proxy cho lượng khách
- Forecast lượng khách hàng tháng
- Forecast với covariates (thời tiết, events)
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Kết quả dự báo."""
    name: str
    point_forecast: np.ndarray
    quantile_forecast: np.ndarray  # (horizon, 10)
    horizon: int
    context_length: int
    last_value: float = 0.0

    @property
    def upper_90(self) -> np.ndarray:
        return self.quantile_forecast[:, -1]

    @property
    def lower_10(self) -> np.ndarray:
        return self.quantile_forecast[:, 1]

    @property
    def median(self) -> np.ndarray:
        return self.quantile_forecast[:, 5]

    @property
    def trend_pct(self) -> float:
        """% thay đổi cuối forecast so với giá trị cuối context."""
        if self.last_value > 0:
            return (self.point_forecast[-1] - self.last_value) / self.last_value * 100
        return 0.0


class TourismForecaster:
    """
    TimesFM 2.5 wrapper cho dự báo du lịch.

    Usage:
        fc = TourismForecaster()
        fc.load_model()
        result = fc.forecast(series, horizon=30, name="Google Trends")
    """

    def __init__(
        self,
        max_context: int = 512,
        max_horizon: int = 128,
    ):
        self.max_context = max_context
        self.max_horizon = max_horizon
        self.model = None

    def load_model(self):
        """Load TimesFM 2.5 từ HuggingFace."""
        import timesfm

        logger.info("🔄 Loading TimesFM 2.5...")
        torch.set_float32_matmul_precision("high")

        self.model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            "google/timesfm-2.5-200m-pytorch"
        )
        self.model.compile(
            timesfm.ForecastConfig(
                max_context=self.max_context,
                max_horizon=self.max_horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            )
        )
        logger.info("✅ Model loaded")

    def _ensure_loaded(self):
        if self.model is None:
            self.load_model()

    def _clean_series(self, series: np.ndarray) -> np.ndarray:
        """Loại NaN, interpolate."""
        s = series.astype(np.float64)
        # Strip leading NaN
        first_valid = np.argmax(~np.isnan(s))
        s = s[first_valid:]
        # Interpolate remaining NaN
        mask = np.isnan(s)
        if mask.any():
            idx = np.arange(len(s))
            s[mask] = np.interp(idx[mask], idx[~mask], s[~mask])
        return s

    def forecast(
        self,
        series: np.ndarray,
        horizon: int = 30,
        name: str = "",
    ) -> ForecastResult:
        """
        Dự báo univariate time series.

        Args:
            series: Array 1D
            horizon: Số bước dự đoán
            name: Tên series (cho metadata)

        Returns:
            ForecastResult
        """
        self._ensure_loaded()
        series = self._clean_series(series)
        h = min(horizon, self.max_horizon)

        point, quantile = self.model.forecast(horizon=h, inputs=[series])

        return ForecastResult(
            name=name,
            point_forecast=point[0, :h],
            quantile_forecast=quantile[0, :h, :],
            horizon=h,
            context_length=len(series),
            last_value=float(series[-1]),
        )

    def forecast_multiple(
        self,
        series_dict: dict[str, np.ndarray],
        horizon: int = 30,
    ) -> dict[str, ForecastResult]:
        """
        Batch forecast nhiều series cùng lúc.

        Args:
            series_dict: {name: array}
            horizon: Số bước dự đoán

        Returns:
            {name: ForecastResult}
        """
        self._ensure_loaded()
        h = min(horizon, self.max_horizon)

        names = list(series_dict.keys())
        inputs = [self._clean_series(series_dict[n]) for n in names]

        points, quantiles = self.model.forecast(horizon=h, inputs=inputs)

        results = {}
        for i, name in enumerate(names):
            results[name] = ForecastResult(
                name=name,
                point_forecast=points[i, :h],
                quantile_forecast=quantiles[i, :h, :],
                horizon=h,
                context_length=len(inputs[i]),
                last_value=float(inputs[i][-1]),
            )
        return results
