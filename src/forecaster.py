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
        """Load TimesFM 2.0 (500M) tu HuggingFace."""
        import timesfm

        logger.info("Loading TimesFM 2.0 (500M)...")
        torch.set_float32_matmul_precision("high")

        # TimesFM 2.0 — 50 transformer layers, 500M params, context 2048
        self.model = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend="cpu",
                per_core_batch_size=32,
                horizon_len=self.max_horizon,
                context_len=min(self.max_context, 2048),
                num_layers=50,
                use_positional_embedding=False,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(
                huggingface_repo_id="google/timesfm-2.0-500m-pytorch",
            ),
        )
        logger.info("Model loaded")

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

        # TimesFM 2.0 API: forecast(inputs, freq) -> (mean, full)
        # full shape: (n_inputs, horizon, 1 + num_quantiles=10)
        # Skip the mean column (idx 0); keep 9 quantiles
        point, full = self.model.forecast(inputs=[series], freq=[1])

        # Pad quantile to 10 cols (model returns 9: q0.1..q0.9). Add q0.5 at front for compat.
        quantile = full[0, :h, 1:]  # shape (h, 9)
        # Insert duplicate of q0.1 at index 0 to match original 10-col layout
        quantile = np.concatenate([quantile[:, :1], quantile], axis=1)

        return ForecastResult(
            name=name,
            point_forecast=point[0, :h],
            quantile_forecast=quantile,
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

        # TimesFM 2.0 API
        points, full = self.model.forecast(inputs=inputs, freq=[1] * len(inputs))

        results = {}
        for i, name in enumerate(names):
            q = full[i, :h, 1:]  # drop mean column, 9 quantile cols
            q = np.concatenate([q[:, :1], q], axis=1)  # pad to 10 cols
            results[name] = ForecastResult(
                name=name,
                point_forecast=points[i, :h],
                quantile_forecast=q,
                horizon=h,
                context_length=len(inputs[i]),
                last_value=float(inputs[i][-1]),
            )
        return results
