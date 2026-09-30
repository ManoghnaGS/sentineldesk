-- Task 4(a): INNER JOIN employees and tickets.
-- Priya Das is absent because she raised zero tickets.
SELECT e.name, e.emp_id, COUNT(t.ticket_id) AS ticket_count
FROM employees AS e
INNER JOIN tickets AS t ON e.emp_id = t.raised_by
GROUP BY e.emp_id, e.name
ORDER BY e.emp_id;
