from sqlalchemy import text, create_engine, Engine
import pandas as pd
import os
from pathlib import Path


SQL_PATH = Path("src/budget_automation/SQL")

class PostgresDatabase:
    def __init__(self):
        self.pg_username = os.getenv("POSTGRES_USER")
        self.pg_password = os.getenv("POSTGRES_PASSWORD")
        self.conn_str = f"postgresql+psycopg2://{self.pg_username}:{self.pg_password}@db:5432/tcpostgres"
        self.engine = create_engine(self.conn_str, pool_size=5, max_overflow=10)


    def reload_new_transactions(self, df: pd.DataFrame) -> None: 
        """Truncate and load the new_transactions table with given DataFrame."""

        with self.engine.begin() as conn:
            # Truncate table to clear current records
            conn.execute(text(open(SQL_PATH / "truncate_new_transactions.sql").read()))

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

        query = text(open(SQL_PATH / "unique_new_transactions.sql").read())
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
