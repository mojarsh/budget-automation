from datetime import datetime
import pandas as pd

import gspread
from google.oauth2 import service_account
from gspread import Worksheet
from pandas import DataFrame


class SheetOperations:
    """Class used to interact with Google Sheets API."""

    def __init__(self, workbook_name: str, worksheet_id: int) -> None:
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        self.creds = service_account.Credentials.from_service_account_file(
            filename="google_creds.json", scopes=self.scope
        )
        self.client = gspread.authorize(self.creds)
        self.workbook_name = workbook_name
        self.worksheet_id = worksheet_id
        self._worksheet: Worksheet | None = None

    def open_sheet(self) -> Worksheet:
        """Method to open and cache the designated worksheet."""

        if self._worksheet is None:
            self._worksheet = self.client.open(self.workbook_name).get_worksheet(self.worksheet_id)

        return self._worksheet

    def get_row_count(self) -> int:
        """Method to get total number of rows in sheet."""

        return int(self.open_sheet().row_count)

    def get_row_data(self, row_num: int) -> list:
        """Method returns data from specified row number."""

        return list(self.open_sheet().row_values(row_num))

    def get_last_entry_date(self) -> datetime:
        """Method returns last entry date in sheet."""

        col_vals = [x for x in self.open_sheet().col_values(2) if x != ""]
        return datetime.strptime(col_vals[-1], "%d/%m/%Y")

    def get_first_blank_row(self) -> int:
        """Find and return the number of the first blank row in the worksheet."""

        return 1 + len(self.open_sheet().col_values(2))

    def write_to_worksheet(self, df: DataFrame) -> None:
        """Write the clean transactions to the worksheet."""

        ws = self.open_sheet()
        df = _clean_transactions_before_export(df)
        ws.update(
            range_name=f"B{self.get_first_blank_row()}:H{self.get_row_count()}",
            values=df.values.tolist(),
            raw=False,
        )

def _clean_transactions_before_export(df: DataFrame) -> DataFrame:
    """Final cleaning and formatting of new transactions before sheets export."""

    # Drop transaction_id and reformat dates before writing to worksheet
    df = df.drop("transaction_id", axis=1)
    df["transaction_date"] = (
        pd.to_datetime(df["transaction_date"]).dt.strftime("%d/%m/%Y")
    )

    return df
