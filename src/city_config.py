"""
City configuration framework for Vietnam tourism forecasting.

Each city provides:
- Coordinates (for weather API)
- Google Trends queries (Vietnamese + English)
- Monthly visitor statistics
- Event calendar
- Revenue data (optional)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CityConfig:
    """Configuration for a Vietnamese city's tourism forecast."""

    # Identity
    city_id: str  # e.g. "danang", "hue"
    city_name: str  # e.g. "Da Nang", "Hue"
    city_name_vi: str  # e.g. "Da Nang", "Thua Thien Hue"

    # Coordinates (for Open-Meteo weather API)
    latitude: float
    longitude: float

    # Google Trends queries — leading indicators
    tourism_queries: dict[str, str] = field(default_factory=dict)
    intl_queries: dict[str, str] = field(default_factory=dict)

    # Monthly visitor data (manual/statistical)
    # Format: {"YYYY-MM": {"total": N, "international": N, "domestic": N}}
    monthly_visitors: dict[str, dict[str, int]] = field(default_factory=dict)

    # Extended monthly metrics (optional, gives forecaster more signal)
    # Format: {"YYYY-MM": {"revenue_billion_vnd": float, "occupancy_pct": float,
    #                       "flights": int, "avg_stay_days": float, "rooms_sold_k": float}}
    monthly_metrics: dict[str, dict[str, float]] = field(default_factory=dict)

    # Quarterly/period revenue data (legacy, optional)
    # Format: {"period_label": value_in_billion_vnd}
    monthly_revenue: dict[str, float] = field(default_factory=dict)

    # Event calendar
    # Format: [{"date": "YYYY-MM-DD", "name": str, "impact": 1-3, "duration_days": int}]
    events: list[dict] = field(default_factory=list)

    @property
    def all_queries(self) -> dict[str, str]:
        return {**self.tourism_queries, **self.intl_queries}


# ═══ CITY REGISTRY ═══

_CITY_REGISTRY: dict[str, CityConfig] = {}


def register_city(config: CityConfig) -> CityConfig:
    """Register a city config in the global registry."""
    _CITY_REGISTRY[config.city_id] = config
    return config


def get_city(city_id: str) -> CityConfig:
    """Get a registered city config by ID."""
    if city_id not in _CITY_REGISTRY:
        available = ", ".join(sorted(_CITY_REGISTRY.keys()))
        raise ValueError(
            f"City '{city_id}' not found. Available: {available}"
        )
    return _CITY_REGISTRY[city_id]


def list_cities() -> list[str]:
    """List all registered city IDs."""
    return sorted(_CITY_REGISTRY.keys())


def load_all_cities():
    """Import all city modules to trigger registration."""
    from src.cities import danang, hue  # noqa: F401
