SELECT
    current_setting('dbeeapp.reference_row_limit')::integer AS row_limit,
    current_setting('dbeeapp.reference_run_label') AS run_label,
    count(*) AS available_rows
FROM reporting.sample_rows;