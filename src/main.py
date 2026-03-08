from budget_automation.config import get_settings
from budget_automation.database import PostgresDatabase
from budget_automation.logger import configure_logging
from budget_automation.sheets import SheetOperations
from budget_automation.starling import AccountOperations, gen_starling_api_headers


def main() -> None:
    """Main function to run end-to-end export process."""

    settings = get_settings()
    logger = configure_logging(settings.log_config_path)
    logger.info("Export process started")
    unique_new_txns = []

    try:
        headers = gen_starling_api_headers()
        ws = SheetOperations(workbook_name="Budget", worksheet_id=4)
        account = AccountOperations(settings.starling_url, headers)

        last_date = ws.get_last_entry_date().strftime("%Y-%m-%dT%H:%M:%SZ")

        new_txns = account.export_transactions(date=last_date)

        if new_txns is not None:

            db = PostgresDatabase()
            unique_new_txns = db.upsert_new_transactions(new_txns)
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
