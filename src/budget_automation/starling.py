import logging
from datetime import UTC, datetime

import pandas as pd
import requests
from pandas import DataFrame, json_normalize

from budget_automation.config import get_settings

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
    "PERSONAL_CARE": "Haircut",
}
COLUMN_NAME_MAPPING = {
    "feedItemUid": "transaction_id",
    "settlementTime": "transaction_date",
    "spendingCategory": "category",
}

logger = logging.getLogger(__name__)


def gen_starling_api_headers() -> dict[str, str]:
    """Read Starling credentials from .env file, and generate API headers."""

    settings = get_settings()

    return {"Authorization": "Bearer " + settings.starling_pat}


class AccountOperations:
    """Class containing methods to access account data via HTTP request."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str],
    ) -> None:
        self.url = url
        self.headers = headers

    @property
    def _account_uid(self) -> str:
        """Property returns Starling Bank account uid."""

        account = requests.get(self.url + "accounts", headers=self.headers, timeout=10)
        return str(account.json()["accounts"][0]["accountUid"])

    def export_transactions(self, date: str) -> DataFrame | None:
        """Export account transactions for specified date range to DataFrame."""
        query_url = (
            f"{self.url}feed/account/{self._account_uid}/"
            f"settled-transactions-between?minTransactionTimestamp={date}&"
            f"maxTransactionTimestamp={datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )
        transactions = requests.get(query_url, headers=self.headers, timeout=10)
        transactions.raise_for_status()
        feed_items: list[dict] = transactions.json()["feedItems"]
        raw_export = json_normalize(feed_items)
        if raw_export.empty:
            logger.info("No new transactions to export")
            return None

        else:
            return _clean_raw_export(raw_export)


def _rename_columns(df: DataFrame) -> DataFrame:
    """Renames columns using mapping dict specified."""

    return df.rename(columns=COLUMN_NAME_MAPPING)


def _parse_dates(df: DataFrame) -> DataFrame:
    """Strips date string from timestamp returned by Starling API."""

    return df.assign(transaction_date=pd.to_datetime(df["transaction_date"].str[:10]).dt.date)


def _apply_mapping(df: DataFrame) -> DataFrame:
    """Apply mappings for transaction status and category."""

    return df.assign(
        status=df["status"].replace(STATUS_MAPPING),
        category=df["category"].replace(CATEGORY_MAPPING),
    )


def _convert_pence_to_pounds(df: DataFrame) -> DataFrame:
    """Convert minorUnits to pounds with vectorised operation."""

    return df.assign(**{"amount.minorUnits": df["amount.minorUnits"] / 100})


def _split_inflow_outflow(df: DataFrame) -> DataFrame:
    """Takes direction, and infers whether transaction is incoming or outgoing."""

    return df.assign(
        inflow=df["amount.minorUnits"].where(df["direction"] == "IN", 0),
        outflow=df["amount.minorUnits"].where(df["direction"] == "OUT", 0),
    )


def _set_default_account(df: DataFrame) -> DataFrame:
    """Set Starling current account as the default for transactions."""

    return df.assign(account="Starling Current Account")


def _filter_columns(df: DataFrame) -> DataFrame:
    """Remove columns not needed for further operations."""

    columns = [
        "transaction_id",
        "transaction_date",
        "outflow",
        "inflow",
        "category",
        "account",
        "reference",
        "status",
    ]

    return df.loc[:, columns]


def _clean_raw_export(df: DataFrame) -> DataFrame:
    """Formats raw transaction df ready for writing to Google Sheets."""

    # Take a working copy of the raw DataFrame
    return (
        df.copy()
        .pipe(_rename_columns)
        .pipe(_parse_dates)
        .pipe(_apply_mapping)
        .pipe(_convert_pence_to_pounds)
        .pipe(_split_inflow_outflow)
        .pipe(_set_default_account)
        .pipe(_filter_columns)
    )
