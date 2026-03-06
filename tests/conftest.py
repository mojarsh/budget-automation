import pandas as pd
import pytest

@pytest.fixture
def raw_transaction_df():
    """Test version of DataFrame format normalised from Starling API response."""

    return pd.DataFrame({
        "feedItemUid": ["uid-001", "uid-002"],
        "settlementTime": ["2026-03-04T10:30:00Z", "2026-03-05T14:00:00Z"],
        "spendingCategory": ["EATING_OUT", "TRANSPORT"],
        "status": ["SETTLED", "SETTLED"],
        "direction": ["IN", "OUT"],
        "amount.minorUnits": [1250, 5000],
        "reference": ["Test Transaction 1", "Test Transaction 2"],
    })

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
