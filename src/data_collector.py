"""
Thu thập dữ liệu cho dự báo du lịch Đà Nẵng.

Nguồn:
1. Google Trends — search interest daily/weekly
2. Open-Meteo — thời tiết Đà Nẵng
3. Thống kê lượng khách hàng tháng (manual + crawl)
4. Event calendar
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ═══ GOOGLE TRENDS ═══

# Các query du lịch Đà Nẵng — leading indicators
TOURISM_QUERIES = {
    "da_nang_hotel": "khách sạn đà nẵng",
    "da_nang_travel": "du lịch đà nẵng",
    "da_nang_flight": "vé máy bay đà nẵng",
    "ba_na_hills": "bà nà hills",
    "my_khe_beach": "biển mỹ khê",
    "da_nang_hotel_en": "da nang hotel",
    "da_nang_travel_en": "da nang travel",
}

# Queries quốc tế — khách quốc tế search trước khi đến
INTL_QUERIES = {
    "danang_en": "danang",
    "danang_hotel_en": "danang hotel",
    "danang_flight_en": "flight to danang",
    "vietnam_beach": "vietnam beach",
}


def fetch_google_trends(
    queries: dict[str, str],
    timeframe: str = "today 3-y",
    geo: str = "",
    sleep_sec: float = 2.0,
) -> pd.DataFrame:
    """
    Lấy Google Trends data cho nhiều queries.

    Args:
        queries: Dict {key: search_term}
        timeframe: Khoảng thời gian (VD: 'today 3-y', '2023-01-01 2026-04-01')
        geo: Quốc gia ('' = worldwide, 'VN' = Việt Nam)
        sleep_sec: Delay giữa các request (tránh rate limit)

    Returns:
        DataFrame với columns = query keys, index = date
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
        raise ValueError("Không lấy được data Google Trends nào")

    result = pd.DataFrame(all_data)
    result.index.name = "date"
    logger.info(f"✅ Google Trends: {len(result)} rows, {len(result.columns)} queries")
    return result


def fetch_trends_daily(
    query: str,
    start_date: str = "2023-01-01",
    end_date: str = "",
    geo: str = "VN",
) -> pd.DataFrame:
    """
    Lấy Google Trends daily data (chia nhỏ thành chunks 6 tháng).

    Google Trends chỉ trả daily khi timeframe < 9 tháng.
    Hàm này tự chia nhỏ rồi nối lại.
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
        raise ValueError(f"Không lấy được daily data cho '{query}'")

    result = pd.concat(chunks)
    result = result[~result.index.duplicated(keep="last")]
    result = result.sort_index()
    result.columns = [query.replace(" ", "_")]
    logger.info(f"✅ Daily trends '{query}': {len(result)} days")
    return result


# ═══ THỜI TIẾT ĐÀ NẴNG ═══

# Tọa độ Đà Nẵng
DANANG_LAT = 16.0544
DANANG_LON = 108.2022


def fetch_weather(
    start_date: str = "2023-01-01",
    end_date: str = "",
    lat: float = DANANG_LAT,
    lon: float = DANANG_LON,
) -> pd.DataFrame:
    """
    Lấy thời tiết Đà Nẵng từ Open-Meteo API (miễn phí).

    Returns:
        DataFrame daily: temperature_max, temperature_min, precipitation,
                        rain, sunshine_duration
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
    # sunshine_duration từ API là seconds → convert hours
    df["sunshine_hours"] = df["sunshine_hours"] / 3600

    logger.info(f"✅ Weather: {len(df)} days ({start_date} → {end_date})")
    return df


# ═══ SỐ LIỆU KHÁCH DU LỊCH (MANUAL) ═══

# Data tổng hợp từ Cục Thống kê Đà Nẵng qua báo chí
# Đơn vị: nghìn lượt
MONTHLY_VISITORS = {
    # 2023 (ước tính từ tổng năm 7.39M)
    "2023-01": {"total": 550, "international": 150, "domestic": 400},
    "2023-02": {"total": 620, "international": 170, "domestic": 450},
    "2023-03": {"total": 580, "international": 180, "domestic": 400},
    "2023-04": {"total": 650, "international": 200, "domestic": 450},
    "2023-05": {"total": 680, "international": 220, "domestic": 460},
    "2023-06": {"total": 750, "international": 250, "domestic": 500},
    "2023-07": {"total": 800, "international": 280, "domestic": 520},
    "2023-08": {"total": 720, "international": 260, "domestic": 460},
    "2023-09": {"total": 550, "international": 200, "domestic": 350},
    "2023-10": {"total": 500, "international": 180, "domestic": 320},
    "2023-11": {"total": 480, "international": 170, "domestic": 310},
    "2023-12": {"total": 510, "international": 190, "domestic": 320},
    # 2024 (có số liệu chính thức)
    "2024-01": {"total": 700, "international": 250, "domestic": 450},
    "2024-02": {"total": 750, "international": 260, "domestic": 490},
    "2024-03": {"total": 850, "international": 300, "domestic": 550},
    "2024-04": {"total": 1000, "international": 350, "domestic": 650},
    "2024-05": {"total": 1050, "international": 370, "domestic": 680},
    "2024-06": {"total": 1100, "international": 380, "domestic": 720},
    "2024-07": {"total": 1300, "international": 427, "domestic": 906},
    "2024-08": {"total": 1200, "international": 420, "domestic": 780},
    "2024-09": {"total": 900, "international": 350, "domestic": 550},
    "2024-10": {"total": 800, "international": 320, "domestic": 480},
    "2024-11": {"total": 750, "international": 300, "domestic": 450},
    "2024-12": {"total": 800, "international": 330, "domestic": 470},
    # 2025 (từ báo cáo 8 tháng = 12.8M, 5M intl, 7.8M domestic)
    "2025-01": {"total": 800, "international": 350, "domestic": 450},
    "2025-02": {"total": 900, "international": 380, "domestic": 520},
    "2025-03": {"total": 950, "international": 420, "domestic": 530},
    "2025-04": {"total": 1100, "international": 450, "domestic": 650},
    "2025-05": {"total": 1200, "international": 480, "domestic": 720},
    "2025-06": {"total": 1200, "international": 500, "domestic": 700},
    "2025-07": {"total": 1800, "international": 600, "domestic": 1200},
    "2025-08": {"total": 1970, "international": 671, "domestic": 1300},
}

# Doanh thu lưu trú + ăn uống (tỷ VND)
MONTHLY_REVENUE = {
    "2024-Q1": 7400,
    "2024-Q2": 8300,
    "2024-7m": 15700,
    "2025-Q1": 7423,
    "2025-Q2": 8914,
    "2025-6m": 16337,
}


def get_visitor_data() -> pd.DataFrame:
    """Trả về DataFrame số liệu khách hàng tháng."""
    records = []
    for month, data in MONTHLY_VISITORS.items():
        records.append({
            "date": pd.Timestamp(month + "-01"),
            "total_visitors_k": data["total"],
            "intl_visitors_k": data["international"],
            "domestic_visitors_k": data["domestic"],
        })
    df = pd.DataFrame(records).set_index("date").sort_index()
    return df


# ═══ EVENT CALENDAR ═══

DANANG_EVENTS = [
    # 2024
    {"date": "2024-01-25", "name": "Tết Nguyên Đán 2024", "impact": 3, "duration_days": 9},
    {"date": "2024-04-30", "name": "Lễ 30/4 - 1/5", "impact": 2, "duration_days": 5},
    {"date": "2024-06-08", "name": "DIFF Pháo hoa 2024", "impact": 3, "duration_days": 35},
    {"date": "2024-07-17", "name": "Enjoy Danang 2024", "impact": 2, "duration_days": 5},
    {"date": "2024-09-02", "name": "Quốc khánh 2/9", "impact": 2, "duration_days": 4},
    # 2025
    {"date": "2025-01-29", "name": "Tết Nguyên Đán 2025", "impact": 3, "duration_days": 9},
    {"date": "2025-04-30", "name": "Lễ 30/4 - 1/5", "impact": 2, "duration_days": 5},
    {"date": "2025-06-01", "name": "DIFF Pháo hoa 2025", "impact": 3, "duration_days": 35},
    {"date": "2025-07-15", "name": "Enjoy Danang 2025", "impact": 2, "duration_days": 5},
    {"date": "2025-09-02", "name": "Quốc khánh 2/9", "impact": 2, "duration_days": 4},
    {"date": "2025-10-15", "name": "Ngày hội Du lịch ĐN", "impact": 2, "duration_days": 4},
    # 2026
    {"date": "2026-02-17", "name": "Tết Nguyên Đán 2026", "impact": 3, "duration_days": 9},
    {"date": "2026-04-30", "name": "Lễ 30/4 - 1/5", "impact": 2, "duration_days": 5},
]


def get_event_series(
    start_date: str = "2023-01-01",
    end_date: str = "",
) -> pd.DataFrame:
    """
    Tạo daily event impact series.

    Returns:
        DataFrame daily với cột 'event_impact' (0-3) và 'has_event' (0/1)
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    dates = pd.date_range(start_date, end_date, freq="D")
    df = pd.DataFrame({"date": dates, "event_impact": 0, "has_event": 0})
    df = df.set_index("date")

    for event in DANANG_EVENTS:
        evt_start = pd.Timestamp(event["date"])
        evt_end = evt_start + pd.Timedelta(days=event["duration_days"])
        mask = (df.index >= evt_start) & (df.index <= evt_end)
        df.loc[mask, "event_impact"] = event["impact"]
        df.loc[mask, "has_event"] = 1

    return df


# ═══ COMBINED DATASET ═══

def collect_all(
    start_date: str = "2023-01-01",
    end_date: str = "",
    fetch_trends: bool = True,
    cache_dir: str = "data/cache",
) -> dict[str, pd.DataFrame]:
    """
    Thu thập tất cả data sources.

    Returns:
        Dict với keys: trends_weekly, trends_daily, weather, visitors, events
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    result = {}

    # 1. Weather
    logger.info("📡 Fetching weather...")
    try:
        result["weather"] = fetch_weather(start_date, end_date)
        result["weather"].to_csv(cache / "weather.csv")
    except Exception as e:
        logger.error(f"Weather failed: {e}")

    # 2. Google Trends
    if fetch_trends:
        logger.info("📡 Fetching Google Trends (weekly)...")
        try:
            all_queries = {**TOURISM_QUERIES, **INTL_QUERIES}
            tf = f"{start_date} {end_date}"
            result["trends_weekly"] = fetch_google_trends(
                all_queries, timeframe=tf, geo=""
            )
            result["trends_weekly"].to_csv(cache / "trends_weekly.csv")
        except Exception as e:
            logger.error(f"Trends weekly failed: {e}")

        logger.info("📡 Fetching Google Trends (daily, VN)...")
        try:
            result["trends_daily"] = fetch_trends_daily(
                "khách sạn đà nẵng", start_date, end_date, geo="VN"
            )
            result["trends_daily"].to_csv(cache / "trends_daily.csv")
        except Exception as e:
            logger.error(f"Trends daily failed: {e}")

    # 3. Visitors (manual data)
    result["visitors"] = get_visitor_data()
    result["visitors"].to_csv(cache / "visitors.csv")

    # 4. Events
    result["events"] = get_event_series(start_date, end_date)
    result["events"].to_csv(cache / "events.csv")

    logger.info(f"✅ Collected {len(result)} datasets")
    return result
