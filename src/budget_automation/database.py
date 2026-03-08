import pandas as pd
from sqlalchemy import create_engine, text

from budget_automation.config import get_settings


class PostgresDatabase:
    def __init__(self):
        self.settings = get_settings()
        self.conn_str = self.settings.database_url
        self.engine = create_engine(self.conn_str, pool_size=5, max_overflow=10)

    def reload_new_transactions(self, df: pd.DataFrame) -> None:
        """Truncate and load the new_transactions table with given DataFrame."""

        with self.engine.begin() as conn:
            # Truncate table to clear current records

            with open(self.settings.sql_dir / "truncate_new_transactions.sql") as f:
                query = f.read()

            conn.execute(text(query))

            # Send all newly loaded transactions to fresh table
            df.to_sql(
                name="new_transactions",
                con=conn,
                schema="budgeting",
                if_exists="append",
                index=False,
                chunksize=500,
            )

    def get_unique_new_transactions(self) -> pd.DataFrame:
        """Query new transactions to find those not already in settled table."""

        with open(self.settings.sql_dir / "truncate_new_transactions.sql") as f:
            query = f.read()

        with self.engine.connect() as conn:
            # Return only new transactions where transaction_id not present in SETTLED_TRANSACTIONS
            return pd.read_sql(query, conn)

    def write_to_settled_transactions(self, df: pd.DataFrame) -> None:
        """Write unique new transactions to settled_transactions table."""

        if not df.empty:
            with self.engine.begin() as conn:
                df.to_sql(
                    name="settled_transactions",
                    con=conn,
                    schema="budgeting",
                    if_exists="append",
                    index=False,
                    chunksize=500,
                )
