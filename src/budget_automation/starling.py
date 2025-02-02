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

        transactions = requests.get(
            self.url
            + "feed/account/"
            + self._account_uid
            + "/settled-transactions-between?"
            + "minTransactionTimestamp="
            + date
            + "&"
            "maxTransactionTimestamp="
            + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            headers=self.headers,
        )
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
    clean_df = df.copy()
    clean_df["amount.minorUnits"] = clean_df["amount.minorUnits"].apply(
        lambda x: x / 100
    )
    clean_df.loc[df["direction"] == "IN", "inflow"] = clean_df["amount.minorUnits"]
    clean_df.loc[df["direction"] == "OUT", "outflow"] = clean_df["amount.minorUnits"]
    clean_df["account"] = "Starling Current Account"
    clean_df = clean_df[
        [
            "feedItemUid",
            "settlementTime",
            "outflow",
            "inflow",
            "spendingCategory",
            "account",
            "reference",
            "status",
        ]
    ]
    clean_df["outflow"] = clean_df["outflow"].fillna(0)
    clean_df["inflow"] = clean_df["inflow"].fillna(0)
    name_mapping = {
        "feedItemUid": "transaction_id",
        "settlementTime": "date",
        "spendingCategory": "category",
    }
    clean_df = clean_df.rename(columns=name_mapping)
    clean_df["date"] = pd.to_datetime(clean_df["date"]).dt.strftime("%d/%m/%Y")
    clean_df["status"] = clean_df["status"].replace(STATUS_MAPPING)
    clean_df["category"] = clean_df["category"].replace(CATEGORY_MAPPING)

    return clean_df
