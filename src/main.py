from sheets import SheetOperations
from starling import AccountOperations, StarlingAPI, clean_export

URL = "https://api.starlingbank.com/api/v2/"


def main() -> None:
    """Main function to call Starling API and return account balance."""
    headers = StarlingAPI().default_headers
    ws = SheetOperations(sheetname="Budget Automation Test", worksheet=4)
    account = AccountOperations(URL, headers)

    last_date = ws.get_last_entry_date()
    transactions = account.export_transactions(date=last_date)

    clean_txns = clean_export(df=transactions)

    return print(clean_txns)


if __name__ == "__main__":
    main()
