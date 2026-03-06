SELECT
    *
FROM
    tcpostgres.budgeting.new_transactions
WHERE
    transaction_id NOT IN (
        SELECT
            transaction_id
        FROM
            tcpostgres.budgeting.settled_transactions
    );

