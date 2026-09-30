# Indexing Notes

## Task 5 — Composite index measurement

The measured query is the exact query from `reports/report_type_status_having.sql`:

```sql
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

### Before creating the index

Command:

```sql
EXPLAIN QUERY PLAN
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

Raw output from the tested SQLite environment:

```text
7|0|0|SCAN tickets
9|0|0|USE TEMP B-TREE FOR GROUP BY
```

### Create the composite index

```sql
CREATE INDEX idx_tickets_type_status
ON tickets(ticket_type, status);
```

### After creating the index

Run the identical `EXPLAIN QUERY PLAN`:

```sql
EXPLAIN QUERY PLAN
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

Raw output from the tested SQLite environment:

```text
7|0|0|SCAN tickets USING COVERING INDEX idx_tickets_type_status
```

### Observation

Before the index, SQLite scans the `tickets` table and builds a temporary B-tree for the `GROUP BY`. After the index, SQLite can scan the covering `(ticket_type, status)` index in the required grouping/sort order, so the separate temporary B-tree is no longer required.

SQLite versions can format the numeric columns of `EXPLAIN QUERY PLAN` slightly differently; the important acceptance-criterion text is `SCAN tickets` plus `USE TEMP B-TREE FOR GROUP BY` before the index, and `SCAN tickets USING COVERING INDEX idx_tickets_type_status` with no temporary GROUP BY step after it.
