"""
Thu thap du lieu cho du bao du lich Viet Nam.

Nguon:
1. Google Trends — search interest daily/weekly
2. Open-Meteo — thoi tiet (any city via lat/lon)
3. Thong ke luong khach hang thang (from CityConfig)
4. Event calendar (from CityConfig)
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

from .city_config import CityConfig

logger = logging.getLogger(__name__)


# ═══ GOOGLE TRENDS ═══

def fetch_google_trends(
    queries: dict[str, str],
    timeframe: str = "today 3-y",
    geo: str = "",
    sleep_sec: float = 2.0,
) -> pd.DataFrame:
    """
    Lay Google Trends data cho nhieu queries.

    Args:
        queries: Dict {key: search_term}
        timeframe: Khoang thoi gian (VD: 'today 3-y', '2023-01-01 2026-04-01')
        geo: Quoc gia ('' = worldwide, 'VN' = Viet Nam)
        sleep_sec: Delay giua cac request (tranh rate limit)

    Returns:
        DataFrame voi columns = query keys, index = date
    """
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl="vi", tz=420)  # GMT+7
    all_data = {}

    for key, term in queries.items():
        try:
            logger.info(f"Fetching Google Trends: '{term}' ({key})")
            pytrends.build_payload([term], timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()
            if not df.empty and term in df.columns:
                all_data[key] = df[term]
            else:
                logger.warning(f"No data for '{term}'")
            time.sleep(sleep_sec)  # Rate limit
        except Exception as e:
            logger.warning(f"Failed '{term}': {e}")
            time.sleep(5)

    if not all_data:
        raise ValueError("Khong lay duoc data Google Trends nao")

    result = pd.DataFrame(all_data)
    result.index.name = "date"
    logger.info(f"Google Trends: {len(result)} rows, {len(result.columns)} queries")
    return result


def fetch_trends_daily(
    query: str,
    start_date: str = "2023-01-01",
    end_date: str = "",
    geo: str = "VN",
) -> pd.DataFrame:
    """
    Lay Google Trends daily data (chia nho thanh chunks 6 thang).

    Google Trends chi tra daily khi timeframe < 9 thang.
    Ham nay tu chia nho roi noi lai.
    """
    from pytrends.request import TrendReq

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    pytrends = TrendReq(hl="vi", tz=420)
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    chunks = []
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=180), end)
        tf = f"{current.strftime('%Y-%m-%d')} {chunk_end.strftime('%Y-%m-%d')}"
        try:
            pytrends.build_payload([query], timeframe=tf, geo=geo)
            df = pytrends.interest_over_time()
            if not df.empty:
                chunks.append(df[[query]])
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Chunk {tf} failed: {e}")
            time.sleep(5)
        current = chunk_end + timedelta(days=1)

    if not chunks:
        raise ValueError(f"Khong lay duoc daily data cho '{query}'")

    result = pd.concat(chunks)
    result = result[~result.index.duplicated(keep="last")]
    result = result.sort_index()
    result.columns = [query.replace(" ", "_")]
    logger.info(f"Daily trends '{query}': {len(result)} days")
    return result


# ═══ THOI TIET (ANY CITY) ═══

def fetch_weather(
    start_date: str = "2023-01-01",
    end_date: str = "",
    lat: float = 16.0544,
    lon: float = 108.2022,
) -> pd.DataFrame:
    """
    Lay thoi tiet tu Open-Meteo API (mien phi).

    Returns:
        DataFrame daily: temp_max, temp_min, precipitation, rain, sunshine_hours
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,sunshine_duration",
        "timezone": "Asia/Ho_Chi_Minh",
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data["daily"])
    df["date"] = pd.to_datetime(df["time"])
    df = df.set_index("date").drop(columns=["time"])
    df.columns = ["temp_max", "temp_min", "precipitation", "rain", "sunshine_hours"]
    # sunshine_duration from API is seconds -> convert hours
    df["sunshine_hours"] = df["sunshine_hours"] / 3600

    logger.info(f"Weather: {len(df)} days ({start_date} -> {end_date})")
    return df


# ═══ SO LIEU KHACH DU LICH (FROM CITY CONFIG) ═══

def get_visitor_data(city: CityConfig) -> pd.DataFrame:
    """
    Tra ve DataFrame so lieu khach hang thang from city config.

    Includes extended metrics when available:
      - revenue_billion_vnd, occupancy_pct, flights, avg_stay_days
    """
    records = []
    for month, data in city.monthly_visitors.items():
        row = {
            "date": pd.Timestamp(month + "-01"),
            "total_visitors_k": data["total"],
            "intl_visitors_k": data["international"],
            "domestic_visitors_k": data["domestic"],
        }
        metrics = city.monthly_metrics.get(month, {})
        row["revenue_billion_vnd"] = metrics.get("revenue_billion_vnd")
        row["occupancy_pct"] = metrics.get("occupancy_pct")
        row["flights"] = metrics.get("flights")
        row["avg_stay_days"] = metrics.get("avg_stay_days")
        records.append(row)
    df = pd.DataFrame(records).set_index("date").sort_index()
    return df


# ═══ EVENT CALENDAR ═══

def get_event_series(
    city: CityConfig,
    start_date: str = "2023-01-01",
    end_date: str = "",
) -> pd.DataFrame:
    """
    Tao daily event impact series from city config.

    Returns:
        DataFrame daily voi cot 'event_impact' (0-3) va 'has_event' (0/1)
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    dates = pd.date_range(start_date, end_date, freq="D")
    df = pd.DataFrame({"date": dates, "event_impact": 0, "has_event": 0})
    df = df.set_index("date")

    for event in city.events:
        evt_start = pd.Timestamp(event["date"])
        evt_end = evt_start + pd.Timedelta(days=event["duration_days"])
        mask = (df.index >= evt_start) & (df.index <= evt_end)
        df.loc[mask, "event_impact"] = event["impact"]
        df.loc[mask, "has_event"] = 1

    return df


# ═══ COMBINED DATASET ═══

def collect_all(
    city: CityConfig,
    start_date: str = "2023-01-01",
    end_date: str = "",
    fetch_trends: bool = True,
    cache_dir: str = "",
) -> dict[str, pd.DataFrame]:
    """
    Thu thap tat ca data sources for a given city.

    Returns:
        Dict voi keys: trends_weekly, trends_daily, weather, visitors, events
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    if not cache_dir:
        cache_dir = f"data/cache/{city.city_id}"
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    result = {}

    # 1. Weather (using city coordinates)
    logger.info(f"Fetching weather for {city.city_name}...")
    try:
        result["weather"] = fetch_weather(
            start_date, end_date,
            lat=city.latitude, lon=city.longitude,
        )
        result["weather"].to_csv(cache / "weather.csv")
    except Exception as e:
        logger.error(f"Weather failed: {e}")

    # 2. Google Trends
    if fetch_trends:
        logger.info(f"Fetching Google Trends (weekly) for {city.city_name}...")
        try:
            tf = f"{start_date} {end_date}"
            result["trends_weekly"] = fetch_google_trends(
                city.all_queries, timeframe=tf, geo=""
            )
            result["trends_weekly"].to_csv(cache / "trends_weekly.csv")
        except Exception as e:
            logger.error(f"Trends weekly failed: {e}")

        # Daily trends — use first tourism query as representative
        if city.tourism_queries:
            first_query = next(iter(city.tourism_queries.values()))
            logger.info(f"Fetching Google Trends (daily, VN): '{first_query}'...")
            try:
                result["trends_daily"] = fetch_trends_daily(
                    first_query, start_date, end_date, geo="VN"
                )
                result["trends_daily"].to_csv(cache / "trends_daily.csv")
            except Exception as e:
                logger.error(f"Trends daily failed: {e}")

    # 3. Visitors (from city config)
    result["visitors"] = get_visitor_data(city)
    result["visitors"].to_csv(cache / "visitors.csv")

    # 4. Events
    result["events"] = get_event_series(city, start_date, end_date)
    result["events"].to_csv(cache / "events.csv")

    logger.info(f"Collected {len(result)} datasets for {city.city_name}")
    return result
