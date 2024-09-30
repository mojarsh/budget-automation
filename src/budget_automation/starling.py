import os
from datetime import datetime, timezone
from enum import StrEnum

import pandas as pd
import requests
from dotenv import load_dotenv
from pandas import DataFrame, json_normalize


class TransactionStatus(StrEnum):
    SETTLED = "✅"
    PENDING = "🅿️"
    RECONCILED = "*️⃣"


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
    def account_uid(self) -> str:
        """Property returns Starling Bank account uid."""

        account = requests.get(self.url + "accounts", headers=self.headers)
        return account.json()["accounts"][0]["accountUid"]

    def current_balance(self) -> int:
        """Obtain current account balance."""

        balance = requests.get(
            self.url + "accounts/" + self.account_uid + "/balance", headers=self.headers
        )
        return balance.json()["effectiveBalance"]["minorUnits"] / 100

    def export_transactions(self, date: str) -> DataFrame:
        """Export account transactions for specified date range to DataFrame."""

        transactions = requests.get(
            self.url
            + "feed/account/"
            + self.account_uid
            + "/settled-transactions-between?"
            + "minTransactionTimestamp="
            + date
            + "&"
            "maxTransactionTimestamp="
            + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            headers=self.headers,
        )
        transactions.raise_for_status()

        return json_normalize(transactions.json()["feedItems"])


def clean_export(df: DataFrame) -> DataFrame:
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
        "settlementTime": "date",
        "spendingCategory": "category",
        "counterPartyName": "payee",
        "reference": "reference",
        "status": "status",
    }

    clean_df = clean_df.rename(columns=name_mapping)

    clean_df["date"] = pd.to_datetime(clean_df["date"]).dt.strftime("%d/%m/%Y")

    status_mapping = {
        "SETTLED": TransactionStatus.SETTLED,
        "PENDING": TransactionStatus.PENDING,
    }

    clean_df["status"] = clean_df["status"].replace(status_mapping)

    return clean_df
