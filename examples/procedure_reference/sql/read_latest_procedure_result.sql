SELECT run_id, run_label, row_limit, rows_seen, completed_at
FROM reporting.dbeeapp_procedure_reference_runs
WHERE run_label = :run_label
ORDER BY run_id DESC
LIMIT 1;
