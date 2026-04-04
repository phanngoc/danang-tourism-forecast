# Du bao Du lich Da Nang — TimesFM 2.5

Framework du bao luong khach du lich Da Nang su dung Google Research TimesFM 2.5.

## Data Sources

| Nguon | Loai | Tan suat | Mien phi |
|---|---|---|---|
| Google Trends | Search interest | Daily/Weekly | Co |
| Open-Meteo | Thoi tiet Da Nang | Daily | Co |
| Cuc Thong ke DN | Luong khach | Monthly | Co (bao chi) |
| Event Calendar | Su kien lon | Manual | Co |

## Chay

```bash
# Full pipeline (ca Google Trends)
python run.py

# Chi dung data offline (nhanh)
python run.py --no-trends

# Custom
python run.py --trends-horizon 24 --visitor-horizon 12
```

## Output

- `output/forecast_*.png` — Charts cho moi query
- `output/forecast_visitors.png` — Du bao luong khach
- `output/dashboard.png` — Dashboard tong hop
- `output/forecast_*.csv` — Data CSV

## Kien truc

```
Google Trends (daily) ─┐
Weather (Open-Meteo) ──┤──> TimesFM 2.5 ──> Forecast + Quantiles
Event Calendar ────────┤                        |
Monthly Visitors ──────┘                    Dashboard / Bot
```
