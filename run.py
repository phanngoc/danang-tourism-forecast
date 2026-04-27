#!/usr/bin/env python3
"""
Chay du bao du lich cho bat ky thanh pho Viet Nam nao.

Usage:
    python run.py                          # Da Nang (default)
    python run.py --city hue               # Hue
    python run.py --city danang --no-trends # Offline mode
    python run.py --city hue --horizon 24  # Forecast 24 weeks trends
    python run.py --list-cities            # List available cities
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.city_config import load_all_cities, list_cities
from src.pipeline import TourismPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    load_all_cities()

    parser = argparse.ArgumentParser(description="Du bao du lich Viet Nam")
    parser.add_argument("--city", default="danang",
                        help=f"City ID (available: {', '.join(list_cities())})")
    parser.add_argument("--list-cities", action="store_true",
                        help="List all available cities")
    parser.add_argument("--start", default="2023-01-01", help="Ngay bat dau data")
    parser.add_argument("--trends-horizon", type=int, default=12, help="So tuan forecast trends")
    parser.add_argument("--visitor-horizon", type=int, default=6, help="So thang forecast khach")
    parser.add_argument("--output", default="", help="Thu muc output (default: output/<city>)")
    parser.add_argument("--no-trends", action="store_true", help="Bo qua Google Trends (offline)")
    args = parser.parse_args()

    if args.list_cities:
        print("Available cities:")
        for city_id in list_cities():
            print(f"  - {city_id}")
        return

    pipeline = TourismPipeline(
        city_id=args.city,
        start_date=args.start,
        trends_horizon=args.trends_horizon,
        visitor_horizon=args.visitor_horizon,
        output_dir=args.output or f"output/{args.city}",
        fetch_trends=not args.no_trends,
    )

    result = pipeline.run()

    print("\n" + "=" * 60)
    print(result.summary_text())
    print("=" * 60)
    print(f"\nCharts + CSV saved to: {result.output_dir}/")


if __name__ == "__main__":
    main()
