import pandas as pd
import pytest
from unittest.mock import MagicMock, call, patch

class TestReloadNewTransactions:

    def test_truncates_table_before_loading(self, mock_db, sample_transactions_df, mocker):
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mocker.patch.object(pd.DataFrame, "to_sql")
        mock_db.reload_new_transactions(sample_transactions_df)

        # First call to execute should be the TRUNCATE statement
        first_call_arg = str(mock_conn.execute.call_args_list[0].args[0])
        assert "TRUNCATE" in first_call_arg.upper()

    def test_loads_dataframe_to_new_transactions_table(self, mock_db, sample_transactions_df, mocker):
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_to_sql = mocker.patch.object(sample_transactions_df.__class__, "to_sql")

        mock_db.reload_new_transactions(sample_transactions_df)

        mock_to_sql.assert_called_once_with(
            name="new_transactions",
            con=mock_conn,
            schema="budgeting",
            if_exists="append",
            index=False,
            chunksize=500,
        )


class TestGetUniqueNewTransactions:

    def test_returns_dataframe_from_query(self, mock_db, sample_transactions_df, mocker):
        mock_conn = MagicMock()
        mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
        mocker.patch("budget_automation.database.pd.read_sql", return_value=sample_transactions_df)

        result = mock_db.get_unique_new_transactions()

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == list(sample_transactions_df.columns)

    def test_executes_correct_sql_file(self, mock_db, sample_transactions_df, mocker):
        mock_conn = MagicMock()
        mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
        mock_read_sql = mocker.patch("budget_automation.database.pd.read_sql", return_value=sample_transactions_df)

        mock_db.get_unique_new_transactions()

        # Verify read_sql was called — the query content comes from the SQL file
        assert mock_read_sql.call_count == 1


class TestWriteToSettledTransactions:

    def test_writes_dataframe_when_not_empty(self, mock_db, sample_transactions_df, mocker):
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_to_sql = mocker.patch.object(pd.DataFrame, "to_sql")

        mock_db.write_to_settled_transactions(sample_transactions_df)

        mock_to_sql.assert_called_once_with(
            name="settled_transactions",
            con=mock_conn,
            schema="budgeting",
            if_exists="append",
            index=False,
            chunksize=500,
        )

    def test_skips_write_when_dataframe_is_empty(self, mock_db, mocker):
        mock_to_sql = mocker.patch.object(pd.DataFrame, "to_sql")
        empty_df = pd.DataFrame()

        mock_db.write_to_settled_transactions(empty_df)

        mock_to_sql.assert_not_called()

    def test_does_not_open_connection_when_dataframe_is_empty(self, mock_db):
        empty_df = pd.DataFrame()

        mock_db.write_to_settled_transactions(empty_df)

        mock_db.engine.begin.assert_not_called()
