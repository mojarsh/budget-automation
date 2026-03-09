import pandas as pd
from sqlalchemy import Column, Date, Float, MetaData, String, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert

from budget_automation.config import get_settings

# Define structure of settled transactions table within budgeting schema
metadata = MetaData(schema="budgeting")

settled_transactions_table = Table(
    "settled_transactions",
    metadata,
    Column("transaction_id", String, primary_key=True),
    Column("transaction_date", Date),
    Column("outflow", Float),
    Column("inflow", Float),
    Column("category", String),
    Column("account", String),
    Column("reference", String),
    Column("status", String),
)

class PostgresDatabase:
    def __init__(self):
        settings = get_settings()
        self.engine = create_engine(settings.database_url, pool_size=5, max_overflow=10)
        self.sql_dir = settings.sql_dir
        self._table = settled_transactions_table

    def upsert_new_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Truncate and load the new_transactions table with given DataFrame."""
        records = df.to_dict(orient="records")

        stmt = (
            insert(self._table)
            .values(records)
            .on_conflict_do_nothing(index_elements=["transaction_id"])
            .returning(text("*"))
        )
        with self.engine.begin() as conn:

            result = conn.execute(stmt)
            inserted = result.fetchall()

        if not inserted:
            return pd.DataFrame(columns=df.columns)

        return pd.DataFrame(inserted, columns=df.columns)
