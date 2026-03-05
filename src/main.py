from pathlib import Path
from sqlalchemy import text, create_engine
import pandas as pd
import os
from budget_automation.logger import configure_logging
from budget_automation.sheets import SheetOperations
from budget_automation.starling import AccountOperations, gen_starling_api_headers

pg_username = os.getenv("POSTGRES_USER")
pg_password = os.getenv("POSTGRES_PASSWORD")

STARLING_URL = "https://api.starlingbank.com/api/v2/"
SQL_PATH = "src/budget_automation/unique_new_transactions.sql"
LOG_CONFIG_PATH = Path("logging_config.json")
DATABASE_URL = (
    f"postgresql+psycopg2://{pg_username}:{pg_password}@db:5432/tcpostgres"
)


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

            engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
            with engine.begin() as conn:
                # Truncate table to clear current records
                conn.execute(text("TRUNCATE TABLE tcpostgres.budgeting.new_transactions;"))

                # Send all newly loaded transactions to fresh table
                new_txns.to_sql(
                    name="new_transactions",
                    con=conn,
                    schema="budgeting",
                    if_exists="append",
                    index=False,
                    chunksize=500,
                )

            # Read SQL query from file
            query = text(open(SQL_PATH).read())
            with engine.connect() as conn:
                # Return only new transactions where transaction_id not present in SETTLED_TRANSACTIONS
                unique_new_txns = pd.read_sql(query, conn)

            if not unique_new_txns.empty:
                with engine.begin() as conn:
                    unique_new_txns.to_sql(
                        name="settled_transactions",
                        con=conn,
                        schema="budgeting",
                        if_exists="append",
                        index=False,
                        chunksize=500,
                    )
                # Drop transaction_id and reformat dates before writing to worksheet
                unique_new_txns = unique_new_txns.drop("transaction_id", axis=1)
                unique_new_txns["transaction_date"] = unique_new_txns["transaction_date"].map(lambda x: f"{x:%d/%m/%Y}")

                ws.write_to_worksheet(unique_new_txns)

            else:
                logger.info("No unique new transactions to write")
                unique_new_txns = []


    except Exception as e:
        logger.error(e)
        raise e

    finally:
        logger.info(f"Export process complete: {len(unique_new_txns)} rows written")


if __name__ == "__main__":
    main()
