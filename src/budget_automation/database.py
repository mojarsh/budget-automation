import pandas as pd
from sqlalchemy import create_engine, text

from budget_automation.config import get_settings


class PostgresDatabase:
    def __init__(self):
        settings = get_settings()
        self.engine = create_engine(settings.database_url, pool_size=5, max_overflow=10)
        self.sql_dir = settings.sql_dir

    def upsert_new_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Truncate and load the new_transactions table with given DataFrame."""

        with self.engine.begin() as conn:

            with open(self.sql_dir / "upsert_new_transactions.sql") as f:
                query = f.read()

            result = conn.execute(text(query), {"rows": list(df.itertuples(index=False, name=None))})
            inserted = result.fetchall()

        if not inserted:
            return pd.DataFrame(columns=df.columns)

        return pd.DataFrame(inserted, columns=df.columns)
