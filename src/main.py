from sheets import SheetOperations
from starling import AccountOperations, clean_export, gen_starling_api_headers


def main() -> None:
    """Main function to call Starling API and return account balance."""
    headers = gen_starling_api_headers()
    ws = SheetOperations(sheetname="Budget Automation Test", worksheet=4)
    account = AccountOperations(headers)

    last_date = ws.get_last_entry_date()
    transactions = account.export_transactions(date=last_date)

    clean_txns = clean_export(df=transactions)

    return print(clean_txns)


if __name__ == "__main__":
    main()
