from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    starling_pat: str
    postgres_user: str
    postgres_password: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "tcpostgres"
    log_config_path: Path = Path("config/logging_config.json")
    category_mapping_path: Path = Path("config/category_mapping.json")
    starling_url: str = "https://api.starlingbank.com/api/v2/"
    sheets_workbook: str = "Budget"
    sheets_worksheet_id: int = 4

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        pw = quote_plus(self.postgres_password)
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{pw}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
