import gspread

from gspread import Worksheet
from datetime import datetime
from google.oauth2 import service_account

class SheetOperations:
    """Class used to interact with Google Sheets API."""

    def __init__(self, sheetname: str, worksheet: int|str) -> None:
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
            ]
        self.creds = service_account.Credentials.from_service_account_file(filename="google_creds.json", scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheetname = sheetname
        self.worksheet = worksheet

    def open_sheet(self) -> Worksheet:
        """Method to open designated worksheet."""

        return self.client.open(self.sheetname).get_worksheet(self.worksheet)
    
    def get_row_count(self) -> int:
        """Method to get total number of rows in sheet."""

        return self.open_sheet().row_count
    
    def get_row_data(self, row_num: int) -> None:
        """Method returns data from specified row number."""

        return self.open_sheet().row_values(row_num)
    
    def get_last_entry_date(self) -> str:
        """Method returns last entry date in sheet."""
        
        col_vals = [x for x in self.open_sheet().col_values(2) if x != ""]
        return datetime.strptime(col_vals[-1], "%d/%m/%Y").strftime("%Y-%m-%dT%H:%M:%SZ")