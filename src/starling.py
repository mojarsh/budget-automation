import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv
from pandas import DataFrame, json_normalize


class StarlingAPI:
    """Class containing methods to generate Starling Bank API credentials."""

    def __init__(self) -> None:
        self.pat
        self.default_headers

    @property
    def pat(self) -> str:
        """Property returns Starling Bank API personal access token."""

        load_dotenv()
        return os.getenv("STARLING_PAT")

    @property
    def default_headers(self) -> dict:
        """Property defined default API headers using personal access token."""

        return {"Authorization": "Bearer " + self.pat}


class AccountOperations:
    """Class containing methods to access account data via HTTP request."""

    def __init__(self, url: str, headers: dict) -> None:
        self.url = url
        self.headers = headers
        self.timestamp_format = "%Y-%m-%dT%H:%M:%SZ"

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
            + datetime.utcnow().strftime(self.timestamp_format),
            headers=self.headers,
        )
        transactions.raise_for_status()

        return json_normalize(transactions.json()["feedItems"])


def clean_export(df: DataFrame) -> DataFrame:
    df_clean = df[
        [
            "settlementTime",
            "spendingCategory",
            "amount.minorUnits",
            "counterPartyName",
            "reference",
            "status",
        ]
    ]

    name_mapping = {
        "settlementTime": "date",
        "spendingCategory": "category",
        "amount.minorUnits": "txn_value",
        "counterPartyName": "payee",
        "reference": "reference",
        "status": "status",
    }

    df_clean.rename(columns=name_mapping, inplace=True)

    df_clean["txn_value"] = df_clean["txn_value"].apply(lambda x: x / 100)

    df_clean["date"] = pd.to_datetime(df_clean["date"])
    df_clean["date"] = df_clean["date"].dt.strftime("%d/%m/%Y")

    return df_clean
