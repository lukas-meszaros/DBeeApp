SELECT row_id, label
FROM reporting.sample_rows
WHERE row_id BETWEEN :minimum_id AND :maximum_id
ORDER BY row_id;
