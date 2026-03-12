from datetime import datetime
from unittest.mock import MagicMock

import pytest

from budget_automation.sheets import SheetOperations


@pytest.fixture
def mock_sheet_ops(mocker):
    """Patches gspread so SheetOperations can be instantiated without credentials."""
    mocker.patch("budget_automation.sheets.service_account.Credentials.from_service_account_file")
    mocker.patch("budget_automation.sheets.gspread.authorize")
    return SheetOperations(workbook_name="Budget", worksheet_id=4)


class TestGetLastEntryDate:
    def test_returns_correct_date(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["Date", "04/03/2026", "05/03/2026"]
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)

        result = mock_sheet_ops.get_last_entry_date()
        assert result == datetime(2026, 3, 5)

    def test_ignores_empty_cells(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["Date", "04/03/2026", ""]
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)

        result = mock_sheet_ops.get_last_entry_date()
        assert result == datetime(2026, 3, 4)


class TestGetFirstBlankRow:
    def test_blank_row_after_data(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["Date", "04/03/2026", "05/03/2026"]
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)

        assert mock_sheet_ops.get_first_blank_row() == 4  # 1 + len(3 items)


class TestGetRowCount:
    def test_returns_row_count(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.row_count = 100
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        assert mock_sheet_ops.get_row_count() == 100

    def test_returns_int(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.row_count = "50"  # gspread may return a string
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        assert isinstance(mock_sheet_ops.get_row_count(), int)


class TestGetRowData:
    def test_returns_row_values(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["04/03/2026", 0.0, 12.50, "Eating Out"]
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        result = mock_sheet_ops.get_row_data(2)
        assert result == ["04/03/2026", 0.0, 12.50, "Eating Out"]

    def test_returns_list(self, mock_sheet_ops):
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["value1", "value2"]
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        assert isinstance(mock_sheet_ops.get_row_data(1), list)


class TestWriteToWorksheet:
    def test_calls_update_with_formatted_data(self, mock_sheet_ops, sample_transactions_df):
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["Date", "04/03/2026"]
        mock_ws.row_count = 1000
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        mock_sheet_ops.write_to_worksheet(sample_transactions_df)
        mock_ws.update.assert_called_once()

    def test_transaction_id_not_written_to_sheet(self, mock_sheet_ops, sample_transactions_df):
        """transaction_id is dropped before writing — it has no place in the spreadsheet."""
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["Date", "04/03/2026"]
        mock_ws.row_count = 1000
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        mock_sheet_ops.write_to_worksheet(sample_transactions_df)
        written_values = mock_ws.update.call_args.kwargs["values"]
        row_length = len(written_values[0]) if written_values else 0
        assert row_length == len(sample_transactions_df.columns) - 1

    def test_dates_formatted_as_strings(self, mock_sheet_ops, sample_transactions_df):
        """Dates are written as formatted strings, not date objects."""
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["Date", "04/03/2026"]
        mock_ws.row_count = 1000
        mock_sheet_ops.open_sheet = MagicMock(return_value=mock_ws)
        mock_sheet_ops.write_to_worksheet(sample_transactions_df)
        written_values = mock_ws.update.call_args.kwargs["values"]
        date_value = written_values[0][0]
        assert isinstance(date_value, str)
