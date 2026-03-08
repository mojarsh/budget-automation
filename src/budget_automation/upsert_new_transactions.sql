INSERT INTO tcpostgres.budgeting.settled_transactions (
    transaction_id, transaction_date, outflow, inflow, category, account, reference, status
)

SELECT
    transaction_id, 
    transaction_date, 
    outflow, 
    inflow,
    category,
    account, 
    reference,
    status
FROM 
    (VALUES :rows) AS t(
    transaction_id, transaction_date, outflow, inflow, category, account, reference, status
)
ON CONFLICT (transaction_id) DO NOTHING
RETURNING *;
