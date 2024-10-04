from budget_automation.sheets import SheetOperations, compute_next_transaction_date
from budget_automation.starling import (
    AccountOperations,
    TransactionStatus,
    clean_export,
    gen_starling_api_headers,
)

STARLING_URL = "https://api.starlingbank.com/api/v2/"
STATUS_MAPPING = {
    "SETTLED": TransactionStatus.SETTLED,
    "PENDING": TransactionStatus.PENDING,
}
PAYMENT_CATEGORY_MAPPING = {
    "INVESTMENTS": "S&S ISA",
    "EATING_OUT": "Eating Out",
    "TRANSPORT": "Public Transport",
    "SHOPPING": "Everything Else",
    "GROCERIES": "Everything Else",
    "ENTERTAINMENT": "Entertainment",
    "BILLS_AND_SERVICES": "Phone Bill",
    "LIFESTYLE": "Everything Else",
    "HOLIDAYS": "Holiday Fund",
    "GENERAL": "Everything Else",
}


def main() -> None:
    """Main function to call Starling API and return account balance."""
    headers = gen_starling_api_headers()
    ws = SheetOperations(sheetname="Budget", worksheet=4)
    account = AccountOperations(url=STARLING_URL, headers=headers)

    last_date = ws.get_last_entry_date()
    export_date = compute_next_transaction_date(last_date)

    txns = account.export_transactions(date=export_date)

    clean_txns = clean_export(
        df=txns,
        status_mapping=STATUS_MAPPING,
        category_mapping=PAYMENT_CATEGORY_MAPPING,
    )

    return ws.write_to_worksheet(clean_txns)


if __name__ == "__main__":
    main()
