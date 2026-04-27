"""
Da Nang city configuration.

Latest data sources (researched April 2026):
- 2025 full year target: 11.9M visitors (4.8M intl, +17%)
- 2025 7-month: 10.7M (4.2M intl, 6.5M domestic)
- 2025 H1: 7.4M; Q1: 2.54M (intl +40% YoY)
- 2025 July: 1.9M total (600K intl, 1.3M domestic)
- 2025 aviation: 48K flights (20.2K intl, 28K domestic)
- 2026 Q1: ~4.1M total (2.3M intl, 1.8M domestic)
- 2026 January: 1.2M+ accommodation (715.8K intl)
- 2026 February: ~1.2M (737K intl)
- 2026 plan: 19.5M total
- 4-5 star hotel occupancy 2025: 65.5%; peak 85-100%
- ADR: ~$112/night
"""

from src.city_config import CityConfig, register_city

DANANG = register_city(CityConfig(
    city_id="danang",
    city_name="Da Nang",
    city_name_vi="Da Nang",
    latitude=16.0544,
    longitude=108.2022,

    tourism_queries={
        "da_nang_hotel": "khach san da nang",
        "da_nang_travel": "du lich da nang",
        "da_nang_flight": "ve may bay da nang",
        "ba_na_hills": "ba na hills",
        "my_khe_beach": "bien my khe",
        "da_nang_hotel_en": "da nang hotel",
        "da_nang_travel_en": "da nang travel",
    },

    intl_queries={
        "danang_en": "danang",
        "danang_hotel_en": "danang hotel",
        "danang_flight_en": "flight to danang",
        "vietnam_beach": "vietnam beach",
    },

    monthly_visitors={
        # 2023 (annual 7.39M, estimated monthly distribution)
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
        # 2024 (annual 10.83M; official monthly approximations)
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
        # 2025 (full year ~12.0M; Q1=2.54M, 7M=10.7M, target 11.9M, intl 4.8M)
        "2025-01": {"total": 800, "international": 350, "domestic": 450},
        "2025-02": {"total": 900, "international": 380, "domestic": 520},
        "2025-03": {"total": 840, "international": 420, "domestic": 420},
        "2025-04": {"total": 1100, "international": 450, "domestic": 650},
        "2025-05": {"total": 1200, "international": 480, "domestic": 720},
        "2025-06": {"total": 1260, "international": 500, "domestic": 760},
        "2025-07": {"total": 1900, "international": 600, "domestic": 1300},
        "2025-08": {"total": 1700, "international": 580, "domestic": 1120},
        "2025-09": {"total": 950, "international": 400, "domestic": 550},
        "2025-10": {"total": 850, "international": 380, "domestic": 470},
        "2025-11": {"total": 800, "international": 360, "domestic": 440},
        "2025-12": {"total": 950, "international": 420, "domestic": 530},
        # 2026 (Q1 ~4.1M, intl 2.3M)
        "2026-01": {"total": 1200, "international": 716, "domestic": 484},
        "2026-02": {"total": 1280, "international": 737, "domestic": 543},
        "2026-03": {"total": 1620, "international": 847, "domestic": 773},
    },

    monthly_metrics={
        # Revenue (billion VND), occupancy (%), flights, avg length of stay (days)
        # 2024 quarterly aggregates distributed evenly
        "2024-01": {"revenue_billion_vnd": 2400, "occupancy_pct": 60, "flights": 3500, "avg_stay_days": 2.1},
        "2024-02": {"revenue_billion_vnd": 2500, "occupancy_pct": 65, "flights": 3600, "avg_stay_days": 2.2},
        "2024-03": {"revenue_billion_vnd": 2500, "occupancy_pct": 62, "flights": 3700, "avg_stay_days": 2.1},
        "2024-04": {"revenue_billion_vnd": 2700, "occupancy_pct": 70, "flights": 3800, "avg_stay_days": 2.3},
        "2024-05": {"revenue_billion_vnd": 2800, "occupancy_pct": 72, "flights": 3850, "avg_stay_days": 2.3},
        "2024-06": {"revenue_billion_vnd": 2800, "occupancy_pct": 75, "flights": 3900, "avg_stay_days": 2.4},
        "2024-07": {"revenue_billion_vnd": 3500, "occupancy_pct": 82, "flights": 4100, "avg_stay_days": 2.5},
        "2024-08": {"revenue_billion_vnd": 3200, "occupancy_pct": 78, "flights": 4000, "avg_stay_days": 2.4},
        "2024-09": {"revenue_billion_vnd": 2400, "occupancy_pct": 60, "flights": 3500, "avg_stay_days": 2.1},
        "2024-10": {"revenue_billion_vnd": 2200, "occupancy_pct": 55, "flights": 3400, "avg_stay_days": 2.0},
        "2024-11": {"revenue_billion_vnd": 2100, "occupancy_pct": 53, "flights": 3300, "avg_stay_days": 2.0},
        "2024-12": {"revenue_billion_vnd": 2300, "occupancy_pct": 58, "flights": 3500, "avg_stay_days": 2.1},
        # 2025 (Q1=7,423; H1=16,337; growing trajectory)
        "2025-01": {"revenue_billion_vnd": 2400, "occupancy_pct": 62, "flights": 3700, "avg_stay_days": 2.2},
        "2025-02": {"revenue_billion_vnd": 2700, "occupancy_pct": 68, "flights": 3850, "avg_stay_days": 2.3},
        "2025-03": {"revenue_billion_vnd": 2323, "occupancy_pct": 62, "flights": 3900, "avg_stay_days": 2.2},
        "2025-04": {"revenue_billion_vnd": 2900, "occupancy_pct": 72, "flights": 4000, "avg_stay_days": 2.4},
        "2025-05": {"revenue_billion_vnd": 3050, "occupancy_pct": 74, "flights": 4050, "avg_stay_days": 2.4},
        "2025-06": {"revenue_billion_vnd": 3869, "occupancy_pct": 76, "flights": 4100, "avg_stay_days": 2.5},
        "2025-07": {"revenue_billion_vnd": 4500, "occupancy_pct": 85, "flights": 4300, "avg_stay_days": 2.6},
        "2025-08": {"revenue_billion_vnd": 4100, "occupancy_pct": 80, "flights": 4200, "avg_stay_days": 2.5},
        "2025-09": {"revenue_billion_vnd": 2700, "occupancy_pct": 63, "flights": 3700, "avg_stay_days": 2.2},
        "2025-10": {"revenue_billion_vnd": 2500, "occupancy_pct": 58, "flights": 3600, "avg_stay_days": 2.1},
        "2025-11": {"revenue_billion_vnd": 2400, "occupancy_pct": 56, "flights": 3500, "avg_stay_days": 2.1},
        "2025-12": {"revenue_billion_vnd": 2800, "occupancy_pct": 64, "flights": 3700, "avg_stay_days": 2.3},
        # 2026 (record Tet; Q1 +18%)
        "2026-01": {"revenue_billion_vnd": 3300, "occupancy_pct": 75, "flights": 4250, "avg_stay_days": 2.4},
        "2026-02": {"revenue_billion_vnd": 3500, "occupancy_pct": 78, "flights": 4280, "avg_stay_days": 2.5},
        "2026-03": {"revenue_billion_vnd": 4200, "occupancy_pct": 78, "flights": 4350, "avg_stay_days": 2.5},
    },

    monthly_revenue={
        "2024-Q1": 7400,
        "2024-Q2": 8300,
        "2024-7m": 15700,
        "2024-full": 28100,
        "2025-Q1": 7423,
        "2025-Q2": 8914,
        "2025-6m": 16337,
        "2025-full": 36000,
        "2026-Q1": 11000,
    },

    events=[
        # 2024
        {"date": "2024-01-25", "name": "Tet Nguyen Dan 2024", "impact": 3, "duration_days": 9},
        {"date": "2024-04-30", "name": "Le 30/4 - 1/5", "impact": 2, "duration_days": 5},
        {"date": "2024-06-08", "name": "DIFF Phao hoa 2024", "impact": 3, "duration_days": 35},
        {"date": "2024-07-17", "name": "Enjoy Danang 2024", "impact": 2, "duration_days": 5},
        {"date": "2024-09-02", "name": "Quoc khanh 2/9", "impact": 2, "duration_days": 4},
        # 2025
        {"date": "2025-01-29", "name": "Tet Nguyen Dan 2025", "impact": 3, "duration_days": 9},
        {"date": "2025-04-30", "name": "Le 30/4 - 1/5", "impact": 2, "duration_days": 5},
        {"date": "2025-06-01", "name": "DIFF Phao hoa 2025", "impact": 3, "duration_days": 35},
        {"date": "2025-07-15", "name": "Enjoy Danang 2025", "impact": 2, "duration_days": 5},
        {"date": "2025-09-02", "name": "Quoc khanh 2/9", "impact": 2, "duration_days": 4},
        {"date": "2025-10-15", "name": "Ngay hoi Du lich DN", "impact": 2, "duration_days": 4},
        {"date": "2025-12-31", "name": "Countdown 2026", "impact": 2, "duration_days": 2},
        # 2026
        {"date": "2026-01-01", "name": "Tan nien 2026", "impact": 2, "duration_days": 3},
        {"date": "2026-02-17", "name": "Tet Nguyen Dan 2026", "impact": 3, "duration_days": 9},
        {"date": "2026-04-30", "name": "Le 30/4 - 1/5", "impact": 2, "duration_days": 5},
        {"date": "2026-06-01", "name": "DIFF Phao hoa 2026", "impact": 3, "duration_days": 35},
        {"date": "2026-07-15", "name": "Enjoy Danang 2026", "impact": 2, "duration_days": 5},
        {"date": "2026-09-02", "name": "Quoc khanh 2/9 (81 nam)", "impact": 2, "duration_days": 4},
    ],
))
