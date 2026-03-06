from pathlib import Path
import pandas as pd
from budget_automation.logger import configure_logging
from budget_automation.sheets import SheetOperations
from budget_automation.starling import AccountOperations, gen_starling_api_headers
from budget_automation.database import PostgresDatabase


STARLING_URL = "https://api.starlingbank.com/api/v2/"
LOG_CONFIG_PATH = Path("logging_config.json")


def main() -> None:
    """Main function to run end-to-end export process."""

    logger = configure_logging(LOG_CONFIG_PATH)
    logger.info("Export process started")
    unique_new_txns = []

    try:
        headers = gen_starling_api_headers()
        ws = SheetOperations(sheetname="Budget", worksheet=4)
        account = AccountOperations(STARLING_URL, headers)

        last_date = ws.get_last_entry_date().strftime("%Y-%m-%dT%H:%M:%SZ")

        new_txns = account.export_transactions(date=last_date)

        if new_txns is not None:

                db = PostgresDatabase()
                db.reload_new_transactions(new_txns)
                unique_new_txns = db.get_unique_new_transactions()
                db.write_to_settled_transactions(unique_new_txns)
                # Drop transaction_id and reformat dates before writing to worksheet
                unique_new_txns = unique_new_txns.drop("transaction_id", axis=1)
                unique_new_txns["transaction_date"] = unique_new_txns["transaction_date"].map(lambda x: f"{x:%d/%m/%Y}")

                ws.write_to_worksheet(unique_new_txns)

        else:
            logger.info("No unique new transactions to write")
            unique_new_txns = []


    except Exception as e:
        logger.error(e)

    finally:
        logger.info(f"Export process complete: {len(unique_new_txns)} rows written")


if __name__ == "__main__":
    main()
