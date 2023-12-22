from starling import StarlingAPI, AccountOperations
from sheets import SheetOperations

URL = "https://api.starlingbank.com/api/v2/"

def main() -> None:
    """Main function to call Starling API and return account balance."""
    headers = StarlingAPI().default_headers
    ws = SheetOperations(sheetname="Budget Automation Test", worksheet=4)
    account = AccountOperations(URL, headers)

    last_date = ws.get_last_entry_date()
    transactions = account.export_transactions(date=last_date)

    transactions_clean = transactions[
        ["settlementTime", 
         "spendingCategory", 
         "counterPartyName", 
         "reference", 
         "amount.minorUnits", 
         "status"]
        ]

    return print(transactions_clean)

if __name__ == "__main__":
    main()