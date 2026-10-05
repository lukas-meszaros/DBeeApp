SELECT
    set_config('dbeeapp.reference_row_limit', :row_limit, false) AS row_limit,
    set_config('dbeeapp.reference_run_label', :run_label, false) AS run_label;
