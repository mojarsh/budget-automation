from unittest.mock import MagicMock

import pandas as pd
import pytest


class TestUpsertTransactions:

    def test_returns_dataframe_of_inserted_rows(self, mock_db, sample_transactions_df):
        """Rows not already in settled_transactions are inserted and returned."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("uid-001", "2026-03-04", 0.0, 12.50, "Eating Out",
             "Starling Current Account", "Pret", "✅"),
            ("uid-002", "2026-03-05", 50.00, 0.0, "Public Transport",
             "Starling Current Account", "Salary", "✅"),
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
             "Starling Current Account", "Pret", "✅"),
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
        """Empty result still has correct column names, not a blank DataFrame."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert list(result.columns) == list(sample_transactions_df.columns)

    def test_returns_inserted_only_if_partial_duplicates(self, mock_db, sample_transactions_df):
        """When some rows are duplicates, only newly inserted rows are returned."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("uid-001", "2026-03-04", 0.0, 12.50, "Eating Out",
             "Starling Current Account", "Pret", "✅"),
        ]

        result = mock_db.upsert_new_transactions(sample_transactions_df)

        assert len(result) == 1
        assert result["transaction_id"].iloc[0] == "uid-001"

    def test_executes_within_transaction(self, mock_db, sample_transactions_df):
        """Upsert runs inside a transaction context (engine.begin)."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        mock_db.engine.begin.assert_called_once()

    def test_executes_single_statement(self, mock_db, sample_transactions_df):
        """A single statement is executed — no staging queries or separate reads."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        assert mock_conn.execute.call_count == 1

    def test_uses_sqlalchemy_insert_construct(self, mock_db, sample_transactions_df, mocker):
        """Execution uses the SQLAlchemy insert construct, not a raw text() statement."""
        from sqlalchemy.dialects.postgresql import Insert
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        executed_stmt = mock_conn.execute.call_args.args[0]
        assert isinstance(executed_stmt, Insert)

    def test_input_converted_to_records_for_insert(self, mock_db, sample_transactions_df, mocker):
        """DataFrame is converted to records before being passed to the insert statement."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_to_dict = mocker.patch.object(
            pd.DataFrame, "to_dict", wraps=sample_transactions_df.to_dict
        )

        mock_db.upsert_new_transactions(sample_transactions_df)

        mock_to_dict.assert_called_once_with(orient="records")

    def test_raises_on_database_error(self, mock_db, sample_transactions_df):
        """Database errors propagate to the caller rather than being swallowed."""
        from sqlalchemy.exc import SQLAlchemyError
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.side_effect = SQLAlchemyError("connection refused")

        with pytest.raises(SQLAlchemyError):
            mock_db.upsert_new_transactions(sample_transactions_df)

    def test_does_not_open_second_connection(self, mock_db, sample_transactions_df):
        """Only one connection is opened — no separate read connection needed."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        assert mock_db.engine.begin.call_count == 1
        mock_db.engine.connect.assert_not_called()

    def test_does_not_use_staging_table(self, mock_db, sample_transactions_df, mocker):
        """No truncate or intermediate table operations are performed."""
        mock_conn = MagicMock()
        mock_db.engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        mock_db.upsert_new_transactions(sample_transactions_df)

        # Only one execute call — no truncate, no staging insert, no separate select
        assert mock_conn.execute.call_count == 1
