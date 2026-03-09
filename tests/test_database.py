from unittest.mock import MagicMock, mock_open

import pandas as pd
import pytest


class TestUpsertTransactions:

    def test_returns_dataframe_of_inserted_rows(self, mock_db, sample_transactions_df):
        """Rows not already in settled_transactions are inserted and returned."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("uid-001", "2026-03-04", 0.0, 12.50, "Eating Out",
             "Starling Current Account", "Test Transaction 1", "✅"),
            ("uid-002", "2026-03-05", 50.00, 0.0, "Public Transport",
             "Starling Current Account", "Test Transaction 2", "✅"),
        ]

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_returns_correct_columns(self, mock_db, sample_transactions_df):
        """Returned DataFrame has the same columns as the input."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("uid-001", "2026-03-04", 0.0, 12.50, "Eating Out",
             "Starling Current Account", "Test Transaction 1", "✅"),
        ]

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert list(result.columns) == list(sample_transactions_df.columns)

    def test_returns_empty_dataframe_when_all_duplicates(self, mock_db, sample_transactions_df):
        """When all rows already exist, an empty DataFrame is returned."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_empty_dataframe_preserves_column_names(self, mock_db, sample_transactions_df):
        """Empty result still has the correct column names, not a blank DataFrame."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert list(result.columns) == list(sample_transactions_df.columns)

    def test_only_new_inserted_if_duplicates(self, mock_db, sample_transactions_df):
        """When some rows are duplicates, only the newly inserted rows are returned."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("uid-001", "2026-03-04", 0.0, 12.50, "Eating Out",
             "Starling Current Account", "Test Transaction 1", "✅"),
        ]

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert len(result) == 1
        assert result["transaction_id"].iloc[0] == "uid-001"

    def test_reads_sql_from_correct_file(self, mock_db, sample_transactions_df, mocker):
        """The upsert SQL is read from upsert_new_transactions.sql, not hardcoded."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_file = mocker.patch(
            "builtins.open",
            mock_open(
                read_data=
                "INSERT INTO settled_transactions ON CONFLICT DO NOTHING RETURNING *"
            )
        )

        mock_db.upsert_new_transactions(sample_transactions_df)

        opened_path = str(mock_file.call_args.args[0])
        assert "upsert_new_transactions.sql" in opened_path

    def test_sql_file_contents_passed_to_execute(self, mock_db, sample_transactions_df, mocker):
        """The contents of the SQL file are what gets executed, not a hardcoded string."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        sql_content = "INSERT INTO settled_transactions ON CONFLICT DO NOTHING RETURNING *"
        mocker.patch("builtins.open", mock_open(read_data=sql_content))

        mock_db.upsert_new_transactions(sample_transactions_df)

        executed_sql = str(mock_conn.execute.call_args.args[0])
        assert sql_content in executed_sql

    def test_executes_within_transaction(self, mock_db, sample_transactions_df):
        """Upsert runs inside a transaction context (engine.begin)."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        mock_db.engine.begin.assert_called_once()

    def test_executes_sql_statement(self, mock_db, sample_transactions_df):
        """A SQL statement is executed against the connection."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        mock_conn.execute.assert_called_once()

    def test_all_input_rows_passed_to_execute(self, mock_db, sample_transactions_df):
        """All rows from the input DataFrame are passed to the SQL statement."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        call_kwargs = mock_conn.execute.call_args.args[1]
        assert len(call_kwargs["rows"]) == len(sample_transactions_df)

    def test_raises_on_database_error(self, mock_db, sample_transactions_df):
        """Database errors are not swallowed — they propagate to the caller."""
        from sqlalchemy.exc import SQLAlchemyError
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.side_effect = SQLAlchemyError("connection refused")

        with pytest.raises(SQLAlchemyError):
            mock_db.upsert_new_transactions(sample_transactions_df)

    def test_raises_on_missing_sql_file(self, mock_db, sample_transactions_df, mocker):
        """A missing SQL file raises FileNotFoundError rather than failing silently."""
        mocker.patch("builtins.open", side_effect=FileNotFoundError)

        with pytest.raises(FileNotFoundError):
            mock_db.upsert_new_transactions(sample_transactions_df)

    def test_does_not_open_second_connection(self, mock_db, sample_transactions_df):
        """Only one database connection is opened — no separate read connection needed."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        assert mock_db.engine.begin.call_count == 1
        mock_db.engine.connect.assert_not_called()
