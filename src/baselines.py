"""
Các model dự báo truyền thống để benchmark so sánh với TimesFM 2.5.

Models:
1. Naive (Last Value) — baseline đơn giản nhất
2. Seasonal Naive — lặp lại pattern mùa vụ
3. Moving Average
4. Exponential Smoothing (Holt-Winters)
5. ARIMA / Auto-ARIMA
6. Prophet (Facebook/Meta)
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


@dataclass
class BaselineForecast:
    """Kết quả forecast từ baseline model."""
    name: str
    point_forecast: np.ndarray
    horizon: int
    train_time_ms: float = 0.0

    @property
    def last_predicted(self) -> float:
        return float(self.point_forecast[-1])


# ═══ 1. NAIVE — Lặp lại giá trị cuối ═══

def naive_forecast(series: np.ndarray, horizon: int) -> BaselineForecast:
    """Dự báo = giá trị cuối cùng lặp lại."""
    return BaselineForecast(
        name="Naive (Last Value)",
        point_forecast=np.full(horizon, series[-1]),
        horizon=horizon,
    )


# ═══ 2. SEASONAL NAIVE — Lặp lại mùa vụ ═══

def seasonal_naive_forecast(
    series: np.ndarray, horizon: int, season_length: int = 12
) -> BaselineForecast:
    """
    Dự báo = lặp lại giá trị cùng kỳ năm trước.
    season_length=12 cho monthly, =52 cho weekly.
    """
    forecast = np.zeros(horizon)
    n = len(series)
    for i in range(horizon):
        idx = n - season_length + (i % season_length)
        if idx >= 0:
            forecast[i] = series[idx]
        else:
            forecast[i] = series[-1]
    return BaselineForecast(
        name=f"Seasonal Naive (s={season_length})",
        point_forecast=forecast,
        horizon=horizon,
    )


# ═══ 3. MOVING AVERAGE ═══

def moving_average_forecast(
    series: np.ndarray, horizon: int, window: int = 6
) -> BaselineForecast:
    """Dự báo = trung bình window điểm cuối."""
    ma = np.mean(series[-window:])
    return BaselineForecast(
        name=f"Moving Average (w={window})",
        point_forecast=np.full(horizon, ma),
        horizon=horizon,
    )


# ═══ 4. EXPONENTIAL SMOOTHING (HOLT-WINTERS) ═══

def exp_smoothing_forecast(
    series: np.ndarray,
    horizon: int,
    seasonal_periods: int = 12,
    trend: str = "add",
    seasonal: str = "add",
) -> BaselineForecast:
    """
    Holt-Winters Exponential Smoothing.
    Hỗ trợ trend + seasonality.
    """
    import time
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    t0 = time.time()
    try:
        model = ExponentialSmoothing(
            series,
            trend=trend,
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        )
        fitted = model.fit(optimized=True, use_brute=True)
        forecast = fitted.forecast(horizon)
        train_ms = (time.time() - t0) * 1000

        return BaselineForecast(
            name=f"Holt-Winters ({trend}/{seasonal}, s={seasonal_periods})",
            point_forecast=np.array(forecast),
            horizon=horizon,
            train_time_ms=train_ms,
        )
    except Exception as e:
        logger.warning(f"Holt-Winters failed: {e}, fallback to simple ES")
        # Fallback: Simple Exponential Smoothing
        from statsmodels.tsa.holtwinters import SimpleExpSmoothing

        model = SimpleExpSmoothing(series)
        fitted = model.fit()
        forecast = fitted.forecast(horizon)
        train_ms = (time.time() - t0) * 1000

        return BaselineForecast(
            name="Simple Exp Smoothing",
            point_forecast=np.array(forecast),
            horizon=horizon,
            train_time_ms=train_ms,
        )


# ═══ 5. ARIMA ═══

def arima_forecast(
    series: np.ndarray,
    horizon: int,
    order: tuple = (2, 1, 2),
    seasonal_order: Optional[tuple] = None,
    seasonal_periods: int = 12,
    auto: bool = True,
) -> BaselineForecast:
    """
    ARIMA / SARIMA forecast.
    auto=True sẽ tự chọn best order.
    """
    import time

    t0 = time.time()

    if auto:
        # Auto ARIMA bằng statsmodels
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        best_aic = np.inf
        best_model = None
        best_order = order

        # Grid search nhỏ
        for p in range(0, 4):
            for d in range(0, 2):
                for q in range(0, 4):
                    try:
                        model = SARIMAX(
                            series, order=(p, d, q),
                            enforce_stationarity=False,
                            enforce_invertibility=False,
                        )
                        fitted = model.fit(disp=False, maxiter=50)
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_model = fitted
                            best_order = (p, d, q)
                    except Exception:
                        continue

        if best_model is None:
            raise ValueError("ARIMA: không tìm được model phù hợp")

        forecast = best_model.forecast(horizon)
        train_ms = (time.time() - t0) * 1000
        return BaselineForecast(
            name=f"Auto-ARIMA {best_order}",
            point_forecast=np.array(forecast),
            horizon=horizon,
            train_time_ms=train_ms,
        )
    else:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        s_order = seasonal_order or (1, 1, 1, seasonal_periods)
        model = SARIMAX(series, order=order, seasonal_order=s_order,
                        enforce_stationarity=False, enforce_invertibility=False)
        fitted = model.fit(disp=False)
        forecast = fitted.forecast(horizon)
        train_ms = (time.time() - t0) * 1000

        return BaselineForecast(
            name=f"SARIMA {order}x{s_order}",
            point_forecast=np.array(forecast),
            horizon=horizon,
            train_time_ms=train_ms,
        )


# ═══ 6. PROPHET ═══

def prophet_forecast(
    series: np.ndarray,
    horizon: int,
    dates: Optional[pd.DatetimeIndex] = None,
    freq: str = "MS",
) -> BaselineForecast:
    """
    Facebook/Meta Prophet forecast.
    Tự detect trend + seasonality + holidays.
    """
    import time
    from prophet import Prophet

    t0 = time.time()

    # Chuẩn bị data cho Prophet (cần columns 'ds' và 'y')
    if dates is not None:
        df = pd.DataFrame({"ds": dates, "y": series})
    else:
        df = pd.DataFrame({
            "ds": pd.date_range("2023-01-01", periods=len(series), freq=freq),
            "y": series,
        })

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=horizon, freq=freq)
    prediction = model.predict(future)
    forecast = prediction["yhat"].iloc[-horizon:].values

    train_ms = (time.time() - t0) * 1000

    return BaselineForecast(
        name="Prophet",
        point_forecast=forecast,
        horizon=horizon,
        train_time_ms=train_ms,
    )


# ═══ BENCHMARK RUNNER ═══

def run_all_baselines(
    series: np.ndarray,
    horizon: int,
    seasonal_periods: int = 12,
    dates: Optional[pd.DatetimeIndex] = None,
    freq: str = "MS",
) -> list[BaselineForecast]:
    """
    Chạy tất cả baseline models.

    Returns:
        List of BaselineForecast
    """
    results = []

    # 1. Naive
    results.append(naive_forecast(series, horizon))
    logger.info(f"  ✅ Naive")

    # 2. Seasonal Naive
    if len(series) >= seasonal_periods:
        results.append(seasonal_naive_forecast(series, horizon, seasonal_periods))
        logger.info(f"  ✅ Seasonal Naive")

    # 3. Moving Average
    results.append(moving_average_forecast(series, horizon, window=min(6, len(series))))
    logger.info(f"  ✅ Moving Average")

    # 4. Holt-Winters
    try:
        if len(series) >= 2 * seasonal_periods:
            results.append(exp_smoothing_forecast(series, horizon, seasonal_periods))
        else:
            results.append(exp_smoothing_forecast(series, horizon, seasonal_periods,
                                                   trend="add", seasonal=None))
        logger.info(f"  ✅ Holt-Winters")
    except Exception as e:
        logger.warning(f"  ❌ Holt-Winters: {e}")

    # 5. Auto-ARIMA
    try:
        results.append(arima_forecast(series, horizon, auto=True))
        logger.info(f"  ✅ Auto-ARIMA")
    except Exception as e:
        logger.warning(f"  ❌ ARIMA: {e}")

    # 6. Prophet
    try:
        results.append(prophet_forecast(series, horizon, dates=dates, freq=freq))
        logger.info(f"  ✅ Prophet")
    except Exception as e:
        logger.warning(f"  ❌ Prophet: {e}")

    return results


def evaluate_all(
    series: np.ndarray,
    forecasts: list[BaselineForecast],
    actual: np.ndarray,
) -> pd.DataFrame:
    """
    So sánh tất cả models.

    Args:
        series: Training data
        forecasts: List kết quả forecast
        actual: Giá trị thực tế

    Returns:
        DataFrame metrics cho mỗi model
    """
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    records = []
    for fc in forecasts:
        pred = fc.point_forecast[:len(actual)]
        act = actual[:len(pred)]

        mae = mean_absolute_error(act, pred)
        rmse = np.sqrt(mean_squared_error(act, pred))
        mask = act != 0
        mape = np.mean(np.abs((act[mask] - pred[mask]) / act[mask])) * 100 if mask.any() else 0

        # Directional accuracy
        if len(act) > 1:
            act_dir = np.diff(act) > 0
            pred_dir = np.diff(pred) > 0
            dir_acc = np.mean(act_dir == pred_dir) * 100
        else:
            dir_acc = 0

        records.append({
            "Model": fc.name,
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE (%)": round(mape, 2),
            "Dir Acc (%)": round(dir_acc, 1),
            "Train (ms)": round(fc.train_time_ms, 0),
        })

    df = pd.DataFrame(records).sort_values("MAE")
    return df
