SELECT application_id, application_name, status
FROM control.applications
WHERE application_name = :name
ORDER BY application_id;
