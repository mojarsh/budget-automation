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
