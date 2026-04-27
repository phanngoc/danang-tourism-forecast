"""
Hue (Thua Thien Hue) city configuration.

Latest data sources (researched April 2026):
- 2024 annual: ~3.9M (1.45M intl, 2.5M domestic), revenue 7,900 ty VND
- 2025 full year: 6.3M total (1.9M intl), revenue 13,000 ty VND, +61.5% YoY (National Tourism Year)
- 2025 H1: 3.33M visitors, revenue 6,370.9 ty VND
- 2025 10 months: 5.39M visitors, 10,700 ty VND
- 2026 target: 7-7.5M total (2.3-2.5M intl), revenue ~15,000 ty VND
- Festival Hue 2026 main: Mar 25 - Apr 7
- 2025 became central-government-managed city
"""

from src.city_config import CityConfig, register_city

HUE = register_city(CityConfig(
    city_id="hue",
    city_name="Hue",
    city_name_vi="Thua Thien Hue",
    latitude=16.4637,
    longitude=107.5909,

    tourism_queries={
        "hue_hotel": "khach san hue",
        "hue_travel": "du lich hue",
        "hue_flight": "ve may bay hue",
        "dai_noi_hue": "dai noi hue",
        "chua_thien_mu": "chua thien mu",
        "lang_tu_duc": "lang tu duc",
        "hue_hotel_en": "hue hotel",
        "hue_travel_en": "hue travel",
    },

    intl_queries={
        "hue_en": "hue vietnam",
        "hue_imperial_en": "hue imperial city",
        "hue_hotel_intl_en": "hue hotel vietnam",
        "hue_festival_en": "hue festival",
    },

    monthly_visitors={
        # 2023 (annual ~3.2M)
        "2023-01": {"total": 240, "international": 80, "domestic": 160},
        "2023-02": {"total": 320, "international": 100, "domestic": 220},
        "2023-03": {"total": 290, "international": 95, "domestic": 195},
        "2023-04": {"total": 310, "international": 110, "domestic": 200},
        "2023-05": {"total": 280, "international": 105, "domestic": 175},
        "2023-06": {"total": 300, "international": 115, "domestic": 185},
        "2023-07": {"total": 320, "international": 120, "domestic": 200},
        "2023-08": {"total": 280, "international": 110, "domestic": 170},
        "2023-09": {"total": 220, "international": 85, "domestic": 135},
        "2023-10": {"total": 200, "international": 75, "domestic": 125},
        "2023-11": {"total": 210, "international": 80, "domestic": 130},
        "2023-12": {"total": 230, "international": 90, "domestic": 140},
        # 2024 (annual 3.9M, Q1=892K, H1=1,950K, 9M=3,100K)
        "2024-01": {"total": 280, "international": 100, "domestic": 180},
        "2024-02": {"total": 340, "international": 120, "domestic": 220},
        "2024-03": {"total": 272, "international": 105, "domestic": 167},
        "2024-04": {"total": 370, "international": 140, "domestic": 230},
        "2024-05": {"total": 340, "international": 130, "domestic": 210},
        "2024-06": {"total": 348, "international": 135, "domestic": 213},
        "2024-07": {"total": 420, "international": 160, "domestic": 260},
        "2024-08": {"total": 380, "international": 145, "domestic": 235},
        "2024-09": {"total": 350, "international": 130, "domestic": 220},
        "2024-10": {"total": 280, "international": 105, "domestic": 175},
        "2024-11": {"total": 260, "international": 95, "domestic": 165},
        "2024-12": {"total": 260, "international": 100, "domestic": 160},
        # 2025 (full year 6.3M, +61.5% YoY, National Tourism Year breakthrough)
        "2025-01": {"total": 450, "international": 150, "domestic": 300},
        "2025-02": {"total": 580, "international": 180, "domestic": 400},
        "2025-03": {"total": 620, "international": 210, "domestic": 410},
        "2025-04": {"total": 720, "international": 240, "domestic": 480},
        "2025-05": {"total": 600, "international": 220, "domestic": 380},
        "2025-06": {"total": 580, "international": 220, "domestic": 360},
        "2025-07": {"total": 720, "international": 250, "domestic": 470},
        "2025-08": {"total": 670, "international": 230, "domestic": 440},
        "2025-09": {"total": 540, "international": 190, "domestic": 350},
        "2025-10": {"total": 510, "international": 185, "domestic": 325},
        "2025-11": {"total": 460, "international": 175, "domestic": 285},
        "2025-12": {"total": 460, "international": 180, "domestic": 280},
        # 2026 (target 7-7.5M, growth from Festival 2026)
        "2026-01": {"total": 530, "international": 200, "domestic": 330},
        "2026-02": {"total": 660, "international": 230, "domestic": 430},
        "2026-03": {"total": 750, "international": 270, "domestic": 480},
    },

    monthly_metrics={
        # Hue revenue distributed from annual figures
        # 2024: 7,900 ty VND total
        "2024-01": {"revenue_billion_vnd": 540, "occupancy_pct": 50, "flights": 800, "avg_stay_days": 1.8},
        "2024-02": {"revenue_billion_vnd": 620, "occupancy_pct": 58, "flights": 850, "avg_stay_days": 1.9},
        "2024-03": {"revenue_billion_vnd": 550, "occupancy_pct": 52, "flights": 870, "avg_stay_days": 1.8},
        "2024-04": {"revenue_billion_vnd": 720, "occupancy_pct": 65, "flights": 900, "avg_stay_days": 2.0},
        "2024-05": {"revenue_billion_vnd": 660, "occupancy_pct": 60, "flights": 880, "avg_stay_days": 1.9},
        "2024-06": {"revenue_billion_vnd": 680, "occupancy_pct": 62, "flights": 900, "avg_stay_days": 2.0},
        "2024-07": {"revenue_billion_vnd": 820, "occupancy_pct": 70, "flights": 950, "avg_stay_days": 2.1},
        "2024-08": {"revenue_billion_vnd": 740, "occupancy_pct": 65, "flights": 920, "avg_stay_days": 2.0},
        "2024-09": {"revenue_billion_vnd": 680, "occupancy_pct": 60, "flights": 870, "avg_stay_days": 1.9},
        "2024-10": {"revenue_billion_vnd": 540, "occupancy_pct": 48, "flights": 800, "avg_stay_days": 1.8},
        "2024-11": {"revenue_billion_vnd": 510, "occupancy_pct": 45, "flights": 780, "avg_stay_days": 1.7},
        "2024-12": {"revenue_billion_vnd": 540, "occupancy_pct": 48, "flights": 820, "avg_stay_days": 1.8},
        # 2025: 13,000 ty VND total (+65% boom from National Tourism Year)
        "2025-01": {"revenue_billion_vnd": 900, "occupancy_pct": 60, "flights": 870, "avg_stay_days": 1.9},
        "2025-02": {"revenue_billion_vnd": 1150, "occupancy_pct": 70, "flights": 920, "avg_stay_days": 2.0},
        "2025-03": {"revenue_billion_vnd": 1230, "occupancy_pct": 72, "flights": 950, "avg_stay_days": 2.1},
        "2025-04": {"revenue_billion_vnd": 1430, "occupancy_pct": 78, "flights": 980, "avg_stay_days": 2.2},
        "2025-05": {"revenue_billion_vnd": 1190, "occupancy_pct": 70, "flights": 950, "avg_stay_days": 2.1},
        "2025-06": {"revenue_billion_vnd": 1150, "occupancy_pct": 68, "flights": 940, "avg_stay_days": 2.1},
        "2025-07": {"revenue_billion_vnd": 1430, "occupancy_pct": 78, "flights": 980, "avg_stay_days": 2.2},
        "2025-08": {"revenue_billion_vnd": 1330, "occupancy_pct": 74, "flights": 960, "avg_stay_days": 2.1},
        "2025-09": {"revenue_billion_vnd": 1080, "occupancy_pct": 65, "flights": 920, "avg_stay_days": 2.0},
        "2025-10": {"revenue_billion_vnd": 1010, "occupancy_pct": 62, "flights": 900, "avg_stay_days": 1.9},
        "2025-11": {"revenue_billion_vnd": 920, "occupancy_pct": 56, "flights": 870, "avg_stay_days": 1.8},
        "2025-12": {"revenue_billion_vnd": 920, "occupancy_pct": 56, "flights": 880, "avg_stay_days": 1.8},
        # 2026 (target 15,000 ty VND, +15-18% growth)
        "2026-01": {"revenue_billion_vnd": 1060, "occupancy_pct": 64, "flights": 920, "avg_stay_days": 2.0},
        "2026-02": {"revenue_billion_vnd": 1310, "occupancy_pct": 73, "flights": 970, "avg_stay_days": 2.1},
        "2026-03": {"revenue_billion_vnd": 1490, "occupancy_pct": 78, "flights": 1000, "avg_stay_days": 2.2},
    },

    monthly_revenue={
        "2024-Q1": 1710.8,
        "2024-full": 7900,
        "2025-H1": 6370.9,
        "2025-10m": 10700,
        "2025-full": 13000,
        "2026-target": 15000,
    },

    events=[
        # 2024
        {"date": "2024-01-25", "name": "Tet Nguyen Dan 2024", "impact": 3, "duration_days": 9},
        {"date": "2024-01-01", "name": "Festival Hue 2024 Khai mac", "impact": 2, "duration_days": 3},
        {"date": "2024-04-30", "name": "Le 30/4 - 1/5", "impact": 2, "duration_days": 5},
        {"date": "2024-04-15", "name": "Festival Hue 2024 - He", "impact": 3, "duration_days": 60},
        {"date": "2024-09-02", "name": "Quoc khanh 2/9", "impact": 2, "duration_days": 4},
        {"date": "2024-09-15", "name": "Festival Hue 2024 - Thu", "impact": 2, "duration_days": 30},
        # 2025 — National Tourism Year
        {"date": "2025-01-01", "name": "Khai mac Nam Du lich QG 2025", "impact": 3, "duration_days": 5},
        {"date": "2025-01-29", "name": "Tet Nguyen Dan 2025", "impact": 3, "duration_days": 9},
        {"date": "2025-03-26", "name": "50 nam Giai phong TT-Hue", "impact": 3, "duration_days": 5},
        {"date": "2025-04-30", "name": "Le 30/4 - 1/5", "impact": 2, "duration_days": 5},
        {"date": "2025-04-15", "name": "Festival Hue 2025 - He", "impact": 3, "duration_days": 60},
        {"date": "2025-09-02", "name": "Quoc khanh 2/9", "impact": 2, "duration_days": 4},
        {"date": "2025-09-15", "name": "Festival Hue 2025 - Thu", "impact": 2, "duration_days": 30},
        {"date": "2025-12-31", "name": "Countdown 2026 - Be mac NDLQG", "impact": 2, "duration_days": 2},
        # 2026 — Festival Hue 2026 (80 events)
        {"date": "2026-01-01", "name": "Khai mac Festival Hue 2026 + Le Ban Soc", "impact": 3, "duration_days": 3},
        {"date": "2026-02-17", "name": "Tet Nguyen Dan 2026 (Xuan Co do)", "impact": 3, "duration_days": 9},
        {"date": "2026-03-25", "name": "Festival Hue 2026 chinh (Tuan le Festival)", "impact": 3, "duration_days": 14},
        {"date": "2026-04-15", "name": "Festival Hue 2026 - He (Kinh thanh toa sang)", "impact": 3, "duration_days": 75},
        {"date": "2026-04-25", "name": "Hoang cung Huyen da", "impact": 2, "duration_days": 5},
        {"date": "2026-04-30", "name": "Le 30/4 - 1/5", "impact": 2, "duration_days": 5},
        {"date": "2026-09-02", "name": "Quoc khanh 2/9", "impact": 2, "duration_days": 4},
        {"date": "2026-09-15", "name": "Festival Hue 2026 - Thu", "impact": 2, "duration_days": 30},
    ],
))
