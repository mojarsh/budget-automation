import pandas as pd
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from budget_automation.database import PostgresDatabase


@pytest.fixture
def raw_transaction_df():
    """Test version of DataFrame format normalised from Starling API response."""

    return pd.DataFrame(
        {
            "feedItemUid": ["uid-001", "uid-002"],
            "settlementTime": ["2026-03-04T10:30:00Z", "2026-03-05T14:00:00Z"],
            "spendingCategory": ["EATING_OUT", "TRANSPORT"],
            "status": ["SETTLED", "SETTLED"],
            "direction": ["IN", "OUT"],
            "amount.minorUnits": [1250, 5000],
            "reference": ["Test Transaction 1", "Test Transaction 2"],
        }
    )


@pytest.fixture
def mock_starling_response():
    """Mocks JSON returned from Starling API - feed."""

    return {
        "feedItems": [
            {
                "feedItemUid": "uid-001",
                "settlementTime": "2026-03-04T10:30:00Z",
                "spendingCategory": "EATING_OUT",
                "status": "SETTLED",
                "direction": "IN",
                "amount.minorUnits": 1250,
                "reference": "Test Transaction 1",
            }
        ]
    }


@pytest.fixture
def mock_accounts_response():
    """Mocks JSON returned from Starling API - accounts."""

    return {"accounts": [{"accountUid": "account-id-abc123"}]}


@pytest.fixture
def mock_db(mocker):
    """Patches get_settings so PostgresDatabase can be instantiated without real credentials."""

    mock_settings = MagicMock()
    mock_settings.database_url = "postgresql+psycopg2://test:test@localhost:5432/test"
    mock_settings.sql_dir = Path("src/budget_automation/SQL")
    mocker.patch("budget_automation.database.get_settings", return_value=mock_settings)
    mocker.patch("budget_automation.database.create_engine")

    return PostgresDatabase()


@pytest.fixture
def sample_transactions_df():
    """A minimal cleaned transactions DataFrame, as produced by _clean_export."""
    return pd.DataFrame(
        {
            "transaction_id": ["uid-001", "uid-002"],
            "transaction_date": ["2026-03-04", "2026-03-05"],
            "outflow": [12.50, 0.0],
            "inflow": [0.0, 50.00],
            "category": ["Eating Out", "Public Transport"],
            "account": ["Starling Current Account", "Starling Current Account"],
            "reference": ["Test Transaction 1", "Test Transaction 2"],
            "status": ["✅", "✅"],
        }
    )
