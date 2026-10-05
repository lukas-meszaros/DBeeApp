CREATE ROLE reporting_user LOGIN PASSWORD 'dbeeapp_reporting_test_only';
CREATE SCHEMA reporting AUTHORIZATION reporting_user;
SET ROLE reporting_user;
CREATE TABLE reporting.application_status (
    application_id integer PRIMARY KEY,
    application_name text NOT NULL,
    status text NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO reporting.application_status (application_id, application_name, status) VALUES
    (101, 'TEST_APP', 'READY'),
    (102, 'PAUSED_APP', 'PAUSED');
INSERT INTO reporting.application_status (application_id, application_name, status)
SELECT 1000 + item,
       'SAMPLE_APP_' || lpad(item::text, 3, '0'),
       CASE WHEN item % 5 = 0 THEN 'PAUSED' ELSE 'READY' END
FROM generate_series(1, 300) AS item;
CREATE TABLE reporting.sample_rows (
    row_id integer PRIMARY KEY,
    label text NOT NULL
);
INSERT INTO reporting.sample_rows
SELECT value, 'row-' || value
FROM generate_series(1, 10000) AS value;
RESET ROLE;
GRANT CONNECT ON DATABASE reporting TO reporting_user;
GRANT USAGE ON SCHEMA reporting TO reporting_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA reporting TO reporting_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA reporting TO reporting_user;
