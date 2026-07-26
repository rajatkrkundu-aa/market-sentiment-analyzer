from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    symbol: str = "^NSEI"
    seed_price: float = 24500.0
    seed_points: int = 30
    history_size: int = 100
    refresh_seconds: int = 5
    default_ma_window: int = 10
