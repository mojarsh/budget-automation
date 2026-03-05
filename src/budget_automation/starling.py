import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from pandas import DataFrame, json_normalize

from budget_automation.logger import configure_logging

LOG_CONFIG_PATH = Path("logging_config.json")

STATUS_MAPPING = {"SETTLED": "✅"}
CATEGORY_MAPPING = {
    "INVESTMENTS": "S&S ISA",
    "EATING_OUT": "Eating Out",
    "TRANSPORT": "Public Transport",
    "SHOPPING": "Everything Else",
    "GROCERIES": "Everything Else",
    "ENTERTAINMENT": "Entertainment",
    "BILLS_AND_SERVICES": "Phone Bill",
    "LIFESTYLE": "Everything Else",
    "HOLIDAYS": "Holiday Fund",
    "GENERAL": "Everything Else",
    "PERSONAL_CARE": "Haircut"
}
COLUMN_NAME_MAPPING = {
        "feedItemUid": "transaction_id",
        "settlementTime": "transaction_date",
        "spendingCategory": "category",
    }

logger = configure_logging(LOG_CONFIG_PATH)


def gen_starling_api_headers() -> dict:
    """Read Starling credentials from .env file, and generate API headers."""

    load_dotenv()
    pat = os.getenv("STARLING_PAT")

    return {"Authorization": "Bearer " + pat}


class AccountOperations:
    """Class containing methods to access account data via HTTP request."""

    def __init__(
        self,
        url: str,
        headers: dict,
    ) -> None:
        self.url = url
        self.headers = headers

    @property
    def _account_uid(self) -> str:
        """Property returns Starling Bank account uid."""

        account = requests.get(self.url + "accounts", headers=self.headers)
        return account.json()["accounts"][0]["accountUid"]

    def export_transactions(self, date: str) -> DataFrame | None:
        """Export account transactions for specified date range to DataFrame."""
        query_url = (
            f"{self.url}feed/account/{self._account_uid}/"
            f"settled-transactions-between?minTransactionTimestamp={date}&"
            f"maxTransactionTimestamp={datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}"
        )
        transactions = requests.get(query_url, headers=self.headers)
        transactions.raise_for_status()
        raw_export = json_normalize(transactions.json()["feedItems"])
        if raw_export.empty:
            logger.info("No new transactions to export")
            return None

        else:
            clean_export = _clean_export(raw_export)

            return clean_export


def _clean_export(df: DataFrame) -> DataFrame:
    """Formats raw transaction df ready for writing to Google Sheets."""

    # Take a working copy of the raw DataFrame
    clean_df = df.copy()

    # Apply mappings to rename columns, statuses and categories
    clean_df = clean_df.rename(columns=COLUMN_NAME_MAPPING)
    clean_df["status"] = clean_df["status"].replace(STATUS_MAPPING)
    clean_df["category"] = clean_df["category"].replace(CATEGORY_MAPPING)

    # Lambda function to convert values from pence to pounds
    clean_df["amount.minorUnits"] = clean_df["amount.minorUnits"].apply(
        lambda x: x / 100
    )

    # Format transaction date as pandas date object
    clean_df["transaction_date"] = pd.to_datetime(clean_df["transaction_date"]).dt.date

    # Assign inflow and outflow amounts to correct columns based on direction, and fill blanks as 0
    clean_df.loc[df["direction"] == "IN", "inflow"] = clean_df["amount.minorUnits"]
    clean_df.loc[df["direction"] == "OUT", "outflow"] = clean_df["amount.minorUnits"]
    clean_df["outflow"] = clean_df["outflow"].fillna(0)
    clean_df["inflow"] = clean_df["inflow"].fillna(0)

    # Set default account value
    clean_df["account"] = "Starling Current Account"

    # Filter to required columns only
    clean_df = clean_df[
        [
            "transaction_id",
            "transaction_date",
            "outflow",
            "inflow",
            "category",
            "account",
            "reference",
            "status",
        ]
    ]

    return clean_df
