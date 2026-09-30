-- Task 4(g): RANK() over ticket count per raiser.
WITH ticket_counts AS (
    SELECT e.emp_id, e.name, COUNT(t.ticket_id) AS ticket_count
    FROM employees AS e
    INNER JOIN tickets AS t ON e.emp_id = t.raised_by
    GROUP BY e.emp_id, e.name
)
SELECT emp_id, name, ticket_count,
       RANK() OVER (ORDER BY ticket_count DESC) AS rank
FROM ticket_counts
ORDER BY rank, emp_id;
