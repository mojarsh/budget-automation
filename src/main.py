from budget_automation.config import get_settings
from budget_automation.database import PostgresDatabase
from budget_automation.logger import configure_logging
from budget_automation.sheets import SheetOperations
from budget_automation.starling import AccountOperations, gen_starling_api_headers


def main() -> None:
    """Main function to run end-to-end export process."""

    settings = get_settings()
    logger = configure_logging(settings.log_config_path)
    logger.info("Export started")

    try:
        headers = gen_starling_api_headers()
        ws = SheetOperations(
            workbook_name=settings.sheets_workbook,
            worksheet_id=settings.sheets_worksheet_id)
        account = AccountOperations(settings.starling_url, headers)

        last_date = ws.get_last_entry_date().strftime("%Y-%m-%dT%H:%M:%SZ")

        new_txns = account.export_transactions(date=last_date)

        if new_txns is not None:

            db = PostgresDatabase()
            unique = db.upsert_new_transactions(new_txns)
            ws.write_to_worksheet(unique)
            logger.info(f"Export complete: {len(unique)} rows written")

        else:
            logger.info("No new transactions to write")

    except Exception as e:
        logger.error(e)
        raise

if __name__ == "__main__":
    main()
