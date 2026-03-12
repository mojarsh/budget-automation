from datetime import date

import pytest
import requests

from budget_automation.starling import AccountOperations, _clean_raw_export


class TestCleanExport:
    def test_pence_converted_to_pounds(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert result["inflow"].iloc[0] == pytest.approx(12.50)

    def test_outflow_direction_assigned_correctly(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert result["inflow"].iloc[0] == pytest.approx(12.50)
        assert result["outflow"].iloc[0] == 0.0

    def test_inflow_direction_assigned_correctly(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert result["outflow"].iloc[1] == pytest.approx(50.00)
        assert result["inflow"].iloc[1] == 0.0

    def test_category_mapping_applied(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert result["category"].iloc[0] == "Eating Out"
        assert result["category"].iloc[1] == "Public Transport"

    def test_unmapped_category_unchanged(self, raw_transaction_df):
        """Categories not in the mapping dict should pass through unchanged."""
        raw_transaction_df["spendingCategory"] = ["UNKNOWN_CAT", "TRANSPORT"]
        result = _clean_raw_export(raw_transaction_df)
        assert result["category"].iloc[0] == "UNKNOWN_CAT"

    def test_status_mapping_applied(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert result["status"].iloc[0] == "✅"

    def test_output_columns_are_correct(self, raw_transaction_df):
        expected_cols = [
            "transaction_id",
            "transaction_date",
            "outflow",
            "inflow",
            "category",
            "account",
            "reference",
            "status",
        ]
        result = _clean_raw_export(raw_transaction_df)
        assert list(result.columns) == expected_cols

    def test_account_column_set_to_default(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert (result["account"] == "Starling Current Account").all()

    def test_transaction_date_is_date_type(self, raw_transaction_df):
        result = _clean_raw_export(raw_transaction_df)
        assert isinstance(result["transaction_date"].iloc[0], date)


class TestAccountOperations:
    def test_account_uid_property(self, mocker, mock_accounts_response):
        mock_get = mocker.patch("budget_automation.starling.requests.get")
        mock_get.return_value.json.return_value = mock_accounts_response

        ops = AccountOperations(url="https://api.example.com/", headers={})
        assert ops._account_uid == "account-id-abc123"

    def test_export_returns_none_when_no_transactions(self, mocker, mock_accounts_response):
        mocker.patch("budget_automation.starling.requests.get").return_value.json.side_effect = [
            mock_accounts_response,
            {"feedItems": []},  # empty response
        ]
        ops = AccountOperations(url="https://api.example.com/", headers={})
        result = ops.export_transactions(date="2026-03-01T00:00:00Z")
        assert result is None

    def test_export_raises_on_http_error(self, mocker, mock_accounts_response):

        mock_get = mocker.patch("budget_automation.starling.requests.get")
        mock_get.return_value.json.return_value = mock_accounts_response
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("401")

        ops = AccountOperations(url="https://api.example.com/", headers={})
        with pytest.raises(requests.HTTPError):
            ops.export_transactions(date="2026-03-04T00:00:00Z")
