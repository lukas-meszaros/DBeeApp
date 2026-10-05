DO $check$
DECLARE
    configured_limit integer := current_setting('dbeeapp.reference_row_limit')::integer;
    available_rows bigint;
BEGIN
    SELECT count(*) INTO available_rows FROM reporting.sample_rows;

    IF configured_limit > available_rows THEN
        RAISE EXCEPTION 'configured row limit % exceeds available sample rows %', configured_limit, available_rows;
    END IF;

    RAISE NOTICE 'Preflight passed: row limit %, available rows %', configured_limit, available_rows;
END;
$check$;
