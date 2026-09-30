-- Task 4(f): type/status combinations having at least three tickets.
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
