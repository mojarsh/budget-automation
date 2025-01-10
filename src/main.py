import sqlite3
from pathlib import Path

from budget_automation.sheets import SheetOperations
from budget_automation.sql import (
    create_sqlite_table_if_not_exists,
    execute_sqlite_query_to_df,
)
from budget_automation.starling import AccountOperations, gen_starling_api_headers

STARLING_URL = "https://api.starlingbank.com/api/v2/"
SQL_PATH = Path("src/budget_automation/SQL")


def main() -> None:
    """Main function to call Starling API and return account balance."""
    headers = gen_starling_api_headers()
    ws = SheetOperations(sheetname="Budget", worksheet=4)
    account = AccountOperations(STARLING_URL, headers)

    last_date = ws.get_last_entry_date().strftime("%Y-%m-%dT%H:%M:%SZ")

    new_txns = account.export_transactions(date=last_date)

    script_mapping = {path.stem: path.read_text() for path in SQL_PATH.iterdir()}

    with sqlite3.connect("transactions.db") as conn:
        # Create base table to store all settled transactions
        create_sqlite_table_if_not_exists(
            conn, script_mapping["create_settled_table"], "SETTLED_TRANSACTIONS"
        )
        # Send all newly loaded transactions to fresh table
        new_txns.to_sql("NEW_TRANSACTIONS", conn, if_exists="replace", index=False)

        # Return only new transactions where transaction_id not present in SETTLED_TRANSACTIONS
        unique_new_transactions = execute_sqlite_query_to_df(
            conn, script_mapping["unique_new_transactions"]
        )
        unique_new_transactions.to_sql(
            "SETTLED_TRANSACTIONS", conn, if_exists="append", index=False
        )

    ws.write_to_worksheet(unique_new_transactions)


if __name__ == "__main__":
    main()
