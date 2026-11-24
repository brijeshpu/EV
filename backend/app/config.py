from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ampwise:ampwise123@localhost:5432/ampwise"
    SIM_SPEED: float = 1.0
    SIM_INTERVAL: float = 2.0
    MAX_RANGE_KM: float = 250.0
    MAX_DIST_KM: float = 100.0
    SAFE_MARGIN_KM: float = 15.0
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "extra": "ignore",
    }


@lru_cache
def get_settings():
    return Settings()
