-- Task 4(d): employees whose ticket count exceeds the scalar-subquery average.
SELECT e.name, e.emp_id, COUNT(t.ticket_id) AS ticket_count
FROM employees AS e
INNER JOIN tickets AS t ON e.emp_id = t.raised_by
GROUP BY e.emp_id, e.name
HAVING COUNT(t.ticket_id) > (
    SELECT AVG(ticket_count)
    FROM (
        SELECT COUNT(t2.ticket_id) AS ticket_count
        FROM employees AS e2
        INNER JOIN tickets AS t2 ON e2.emp_id = t2.raised_by
        GROUP BY e2.emp_id
    )
)
ORDER BY e.emp_id;
