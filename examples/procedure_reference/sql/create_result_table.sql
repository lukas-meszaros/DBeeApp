CREATE TABLE IF NOT EXISTS reporting.dbeeapp_procedure_reference_runs (
    run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_label text NOT NULL,
    row_limit integer NOT NULL,
    rows_seen bigint NOT NULL,
    completed_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
