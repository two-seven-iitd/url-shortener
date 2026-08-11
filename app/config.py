from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "https://xoragain.com"
    port: int = 8000

    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql://dev:devpass@localhost:5432/shortener"

    geoip_db_path: str = "data/GeoLite2-City.mmdb"

    default_rate_limit_per_minute: int = 60
    default_cache_ttl_seconds: int = 86400
    min_code_length: int = 4


settings = Settings()
