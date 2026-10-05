CREATE ROLE control_user LOGIN PASSWORD 'dbeeapp_control_test_only';
CREATE SCHEMA control AUTHORIZATION control_user;
SET ROLE control_user;
CREATE TABLE control.applications (
    application_id integer PRIMARY KEY,
    application_name text UNIQUE NOT NULL,
    status text NOT NULL
);
INSERT INTO control.applications VALUES
    (101, 'TEST_APP', 'READY'),
    (102, 'PAUSED_APP', 'PAUSED');
CREATE TABLE control.account (
    account_id integer PRIMARY KEY,
    balance integer NOT NULL
);
INSERT INTO control.account VALUES (1, 100), (2, 50);
CREATE TABLE control.audit_log (
    event_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
RESET ROLE;
GRANT CONNECT ON DATABASE control TO control_user;
GRANT USAGE ON SCHEMA control TO control_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA control TO control_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA control TO control_user;
