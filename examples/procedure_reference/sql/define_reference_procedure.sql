CREATE OR REPLACE PROCEDURE reporting.dbeeapp_reference_procedure()
LANGUAGE plpgsql
AS $procedure$
DECLARE
    configured_limit integer;
    configured_label text;
    rows_seen bigint;
    new_run_id bigint;
BEGIN
    configured_limit := current_setting('dbeeapp.reference_row_limit')::integer;
    configured_label := current_setting('dbeeapp.reference_run_label');

    SELECT count(*)
    INTO rows_seen
    FROM reporting.sample_rows
    WHERE row_id <= configured_limit;

    INSERT INTO reporting.dbeeapp_procedure_reference_runs (run_label, row_limit, rows_seen)
    VALUES (configured_label, configured_limit, rows_seen)
    RETURNING run_id INTO new_run_id;

    RAISE NOTICE 'Procedure run % (%): counted % sample rows up to row_id %',
        new_run_id, configured_label, rows_seen, configured_limit;
END;
$procedure$;
