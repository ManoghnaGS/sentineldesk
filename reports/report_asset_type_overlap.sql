-- Task 4(e): assets with at least one incident OR maintenance ticket.
SELECT asset_id
FROM assets
WHERE asset_id IN (
    SELECT asset_id FROM tickets
    WHERE ticket_type = 'incident' AND asset_id IS NOT NULL
)
UNION
SELECT asset_id
FROM assets
WHERE asset_id IN (
    SELECT asset_id FROM tickets
    WHERE ticket_type = 'maintenance' AND asset_id IS NOT NULL
)
ORDER BY asset_id;

-- Incident assets that are not maintenance assets.
SELECT asset_id
FROM assets
WHERE asset_id IN (
    SELECT asset_id FROM tickets
    WHERE ticket_type = 'incident' AND asset_id IS NOT NULL
)
EXCEPT
SELECT asset_id
FROM assets
WHERE asset_id IN (
    SELECT asset_id FROM tickets
    WHERE ticket_type = 'maintenance' AND asset_id IS NOT NULL
)
ORDER BY asset_id;
