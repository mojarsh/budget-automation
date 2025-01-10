from sqlite3 import Connection

from pandas import DataFrame


def execute_sqlite_query_to_df(conn: Connection, query: str) -> DataFrame:

    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]
    df = DataFrame(results, columns=col_names)
    if results:
        return df


def create_sqlite_table_if_not_exists(
    conn: Connection, query: str, table_name: str
) -> None:
    table_name_dict = {"table_name": table_name}
    cursor = conn.cursor()
    cursor.execute(query, table_name_dict)
    conn.commit()
