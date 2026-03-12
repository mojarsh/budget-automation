from decimal import Decimal

import pandas as pd
from sqlalchemy import Column, Date, Float, MetaData, String, Table, create_engine, literal_column
from sqlalchemy.dialects.postgresql import insert

from budget_automation.config import get_settings


class PostgresDatabase:
    def __init__(self) -> None:
        settings = get_settings()
        self.engine = create_engine(settings.database_url, pool_size=5, max_overflow=10)
        self._table = Table(
            "settled_transactions",
            MetaData(schema="budgeting"),
            Column("transaction_id", String, primary_key=True),
            Column("transaction_date", Date),
            Column("outflow", Float),
            Column("inflow", Float),
            Column("category", String),
            Column("account", String),
            Column("reference", String),
            Column("status", String),
        )

    def upsert_new_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Insert new transactions, skip duplicates and return inserted rows."""
        records = df.to_dict(orient="records")

        with self.engine.begin() as conn:
            result = conn.execute(
                insert(self._table)
                .values(records)
                .on_conflict_do_nothing(index_elements=["transaction_id"])
                .returning(literal_column("*"))
            )
            inserted = result.fetchall()

        if not inserted:
            return pd.DataFrame(columns=df.columns)

        result_df = pd.DataFrame(inserted, columns=df.columns)
        decimal_cols = [
            col
            for col in result_df.columns
            if not result_df[col].empty and isinstance(result_df[col].iloc[0], Decimal)
        ]
        result_df[decimal_cols] = result_df[decimal_cols].astype(float)

        return result_df
