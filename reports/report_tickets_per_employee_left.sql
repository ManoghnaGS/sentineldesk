-- Task 4(b): LEFT JOIN with both COUNT(*) and COUNT(t.ticket_id).
-- COUNT(*) counts the NULL-padded joined row; COUNT(t.ticket_id) counts real tickets.
SELECT e.name, e.emp_id, COUNT(*) AS row_count, COUNT(t.ticket_id) AS ticket_count
FROM employees AS e
LEFT JOIN tickets AS t ON e.emp_id = t.raised_by
GROUP BY e.emp_id, e.name
ORDER BY e.emp_id;
