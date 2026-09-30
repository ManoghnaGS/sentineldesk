-- Task 4(c): ticket count per asset, including zero-ticket assets.
SELECT a.asset_id, a.asset_tag, COUNT(t.ticket_id) AS ticket_count
FROM assets AS a
LEFT JOIN tickets AS t ON a.asset_id = t.asset_id
GROUP BY a.asset_id, a.asset_tag
ORDER BY a.asset_id;

-- Independent confirmation that AST-018 has no matching non-NULL ticket asset_id.
SELECT a.asset_id, a.asset_tag
FROM assets AS a
WHERE a.asset_id = 18
  AND a.asset_id NOT IN (
      SELECT DISTINCT asset_id
      FROM tickets
      WHERE asset_id IS NOT NULL
  );
