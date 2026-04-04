#!/usr/bin/env python3
"""
Chạy dự báo du lịch Đà Nẵng.

Usage:
    python run.py                    # Full pipeline (có Google Trends)
    python run.py --no-trends        # Chỉ dùng data offline (nhanh, không cần internet cho trends)
    python run.py --horizon 24       # Forecast 24 weeks trends
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import DanangTourismPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="Du bao du lich Da Nang")
    parser.add_argument("--start", default="2023-01-01", help="Ngay bat dau data")
    parser.add_argument("--trends-horizon", type=int, default=12, help="So tuan forecast trends")
    parser.add_argument("--visitor-horizon", type=int, default=6, help="So thang forecast khach")
    parser.add_argument("--output", default="output", help="Thu muc output")
    parser.add_argument("--no-trends", action="store_true", help="Bo qua Google Trends (offline)")
    args = parser.parse_args()

    pipeline = DanangTourismPipeline(
        start_date=args.start,
        trends_horizon=args.trends_horizon,
        visitor_horizon=args.visitor_horizon,
        output_dir=args.output,
        fetch_trends=not args.no_trends,
    )

    result = pipeline.run()

    print("\n" + "=" * 60)
    print(result.summary_text())
    print("=" * 60)
    print(f"\nCharts + CSV saved to: {args.output}/")


if __name__ == "__main__":
    main()
