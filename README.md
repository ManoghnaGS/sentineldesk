# SentinelDesk — An Internal IT Asset & Ticket Management Platform

SentinelDesk is an internal IT asset and support-ticket management platform built to replace spreadsheet-based tracking of employees, assets, support tickets, ticket history, reporting, and database operations.

This repository contains the complete submission for Parts 1–3:

- Part 1 — Domain Model & In-Memory Engine
- Part 2 — Persistent Database Layer, Transactions & Reporting
- Part 3 — HLD/LLD & Scale-Readiness Design

The project uses Python's standard library, SQLite, SQL, threading, and Mermaid diagrams rendered by GitHub. No paid account, API key, server, or third-party paid service is required.

---

## Repository Structure

```text
sentineldesk/
│
├── README.md
├── engine.py
├── schema.sql
├── seed_data.sql
├── repository.py
├── run_concurrency_experiment.py
│
├── reports/
│   ├── report_tickets_per_employee_inner.sql
│   ├── report_tickets_per_employee_left.sql
│   ├── report_asset_ticket_coverage.sql
│   ├── report_employees_above_average.sql
│   ├── report_asset_type_overlap.sql
│   ├── report_type_status_having.sql
│   └── report_employee_rank_window.sql
│
├── INDEXING_NOTES.md
└── DESIGN.md
```

---

# Requirements

Install Python 3.10 or newer.

Check the version:

```bash
python --version
```

The implementation uses only Python standard-library modules including:

- `abc`
- `dataclasses`
- `datetime`
- `sqlite3`
- `threading`
- `tempfile`
- `time`

---

# Setup

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/sentineldesk.git
cd sentineldesk
```

Replace `YOUR-USERNAME` with the GitHub username that owns this repository.

---

# Part 1 — Domain Model & In-Memory Engine

Part 1 is implemented in:

```text
engine.py
```

## Domain Model

The abstract `Ticket` class inherits from `ABC` and contains:

```text
ticket_id
asset_id
raised_by
priority
status
created_at
resolved_at
```

It declares:

```python
@abstractmethod
def resolution_checklist(self) -> list[str]:
    ...
```

The concrete ticket types are:

```text
IncidentTicket
ServiceRequestTicket
MaintenanceTicket
```

Each subclass provides a different `resolution_checklist()` appropriate to its ticket type.

`Ticket.age_in_days(reference)` calculates the number of calendar days between `created_at` and the supplied `YYYY-MM-DD` reference date.

`Employee` and `Asset` are plain data classes using the required field names and types.

`HelpdeskEngine` maintains:

```python
employees_by_id
assets_by_id
tickets_by_status
ticket_type_seen
count_by_type_status
```

`HelpdeskEngine.load_from_db()` reads SQLite rows and creates the correct concrete ticket subclass based on `ticket_type`. It never instantiates `Ticket` directly.

The `notify(ticket)` function calls the ticket's `resolution_checklist()` method.

## Run Part 1

```bash
python engine.py
```

Expected validation output:

```text
PASS: Ticket is abstract and cannot be instantiated.
PASS: age_in_days() returned 8.
PASS: all three ticket subclasses provide distinct checklists.
PASS: notify() works for all Ticket subclasses.
Part 1 basic tests completed successfully.
```

---

# Part 2 — Persistent Database Layer, Transactions & Reporting

Part 2 is divided into five tasks.

---

# Task 1 — Schema and Seed Data

## `schema.sql`

The database schema is defined in:

```text
schema.sql
```

The schema satisfies Third Normal Form (3NF): every non-key attribute depends on the whole primary key, and there are no transitive dependencies among non-key attributes. For example, `department` and `role` in `employees` depend directly on `emp_id`, while asset assignment and ticket relationships use foreign keys rather than repeating employee details.

The four tables are:

```text
employees
assets
tickets
ticket_status_history
```

The `tickets` table includes:

```text
ticket_id
asset_id
raised_by
ticket_type
priority
status
created_at
resolved_at
reopen_count
```

The `ticket_status_history` table records ticket status changes.

## `seed_data.sql`

The exact seed data supplied by the project brief is stored in:

```text
seed_data.sql
```

It inserts:

```text
12 employees
18 assets
30 tickets
```

For every ticket there is one creation history row:

```text
old_status = NULL
new_status = Open
changed_at = created_at
```

For every seeded ticket whose final status is not `Open`, a second history row is inserted:

```text
old_status = Open
new_status = seeded final status
changed_at = resolved_at when available, otherwise created_at
```

Exactly 20 of the 30 tickets have a non-Open seeded status, so:

```text
30 creation rows + 20 status-change rows = 50 ticket_status_history rows
```

## Create a fresh SQLite database

Use a fresh database for reproducible results.

On Windows, macOS, or Linux, this Python command creates the database from the two SQL files:

```bash
python -c "import sqlite3; c=sqlite3.connect('sentineldesk.db'); c.executescript(open('schema.sql').read()); c.executescript(open('seed_data.sql').read()); c.close()"
```

Alternatively, if the SQLite command-line program is installed:

```bash
sqlite3 sentineldesk.db < schema.sql
sqlite3 sentineldesk.db < seed_data.sql
```

## Verify Task 1

Run:

```bash
python -c "import sqlite3; c=sqlite3.connect('sentineldesk.db'); print('employees =', c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]); print('assets =', c.execute('SELECT COUNT(*) FROM assets').fetchone()[0]); print('tickets =', c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]); print('ticket_status_history =', c.execute('SELECT COUNT(*) FROM ticket_status_history').fetchone()[0]); c.close()"
```

Expected output:

```text
employees = 12
assets = 18
tickets = 30
ticket_status_history = 50
```

---

# Task 2 — Transactional Write Path (Atomicity)

The transactional repository is implemented in:

```text
repository.py
```

The class is:

```python
class Repository:
```

Its main method is:

```python
update_ticket_status(conn, ticket_id, new_status)
```

The method performs these operations in one transaction:

1. Reads the current ticket status.
2. Updates `tickets.status`.
3. Inserts a matching row into `ticket_status_history`.
4. Commits only if all operations succeed.
5. Rolls back the entire transaction if an exception occurs.

The method therefore prevents a ticket update from being committed without its corresponding history row.

## Run the atomicity test

```bash
python repository.py
```

Expected output:

```text
Before successful call: ('Open', 0)
After successful call: ('Resolved', 1)
Expected failure: CHECK constraint failed: status IN ('Open','InProgress','Resolved','Closed')
Before failing call: ('Resolved', 1)
After failing call: ('Resolved', 1)
PASS: successful call changed one ticket and added one history row.
PASS: failed call changed zero rows in either table.
Atomicity test completed successfully.
```

The deliberately invalid status:

```text
Cancelled
```

violates the `tickets.status` CHECK constraint.

The failed transaction is rolled back, leaving both tables unchanged by the failed attempt.

---

# Task 3 — Concurrency Experiment

The concurrency experiment is implemented in:

```text
run_concurrency_experiment.py
```

The script uses two `threading.Thread` workers.

Each worker operates on the same ticket and performs a read-modify-write operation on:

```text
reopen_count
```

## Naive version

The naive version does not wrap the read and write in one explicit transaction.

Both workers can read:

```text
reopen_count = 0
```

before either writes.

Both then calculate:

```text
0 + 1 = 1
```

and write `1`.

This reproduces the lost-update anomaly.

## Safe version

The safe version uses:

```sql
BEGIN IMMEDIATE
```

before reading and writing.

`BEGIN IMMEDIATE` obtains SQLite's write-reservation lock before the read-modify-write sequence proceeds. The second worker waits for the first transaction to commit, then reads the newly committed value and increments it.

The correct final result is therefore:

```text
2
```

## Run the experiment

```bash
python run_concurrency_experiment.py
```

Expected output:

```text
Naive final reopen_count values:
Trial 1: 1
Trial 2: 1
Trial 3: 1
Trial 4: 1
Trial 5: 1

Safe (BEGIN IMMEDIATE) final reopen_count values:
Trial 1: 2
Trial 2: 2
Trial 3: 2
Trial 4: 2
Trial 5: 2

PASS: naive version reproduced the lost-update result 1 in all 5 trials.
PASS: BEGIN IMMEDIATE version produced the correct result 2 in all 5 trials.
```

The experiment creates fresh isolated temporary SQLite databases, so it does not modify the Part 1/Task 1 seeded database.

---

# Task 4 — SQL Reports

All seven required reports are stored as individual `.sql` files under:

```text
reports/
```

## Report (a) — Tickets per employee using INNER JOIN

File:

```text
reports/report_tickets_per_employee_inner.sql
```

Purpose:

- INNER JOIN `employees` and `tickets`
- Group tickets by employee
- Return only employees who raised at least one ticket

Expected raw output:

```text
Aarav Sharma|1|7
Isha Verma|2|1
Rohan Gupta|3|1
Diya Nair|4|1
Kabir Singh|5|1
Meera Iyer|6|2
Vivaan Rao|7|4
Ananya Joshi|8|1
Aditya Menon|9|3
Sara Khan|10|2
Arjun Reddy|11|7
```

There are exactly 11 rows. Priya Das (`emp_id = 12`) is absent because she raised zero tickets.

---

## Report (b) — Tickets per employee using LEFT JOIN

File:

```text
reports/report_tickets_per_employee_left.sql
```

The query returns both:

```text
COUNT(*)
COUNT(t.ticket_id)
```

Expected raw output:

```text
Aarav Sharma|1|7|7
Isha Verma|2|1|1
Rohan Gupta|3|1|1
Diya Nair|4|1|1
Kabir Singh|5|1|1
Meera Iyer|6|2|2
Vivaan Rao|7|4|4
Ananya Joshi|8|1|1
Aditya Menon|9|3|3
Sara Khan|10|2|2
Arjun Reddy|11|7|7
Priya Das|12|1|0
```

For Priya Das:

```text
COUNT(*) = 1
COUNT(t.ticket_id) = 0
```

The difference occurs because a LEFT JOIN creates one NULL-padded joined row for an employee with no matching ticket. `COUNT(*)` counts that row, while `COUNT(t.ticket_id)` counts only non-NULL ticket IDs.

---

## Report (c) — Asset ticket coverage

File:

```text
reports/report_asset_ticket_coverage.sql
```

Expected output of the first query:

```text
1|AST-001|2
2|AST-002|4
3|AST-003|1
4|AST-004|1
5|AST-005|2
6|AST-006|3
7|AST-007|0
8|AST-008|2
9|AST-009|0
10|AST-010|1
11|AST-011|2
12|AST-012|1
13|AST-013|0
14|AST-014|0
15|AST-015|0
16|AST-016|0
17|AST-017|1
18|AST-018|0
```

The independent `NOT IN` confirmation returns:

```text
18|AST-018
```

This confirms that AST-018 has no matching non-NULL `asset_id` in `tickets`.

---

## Report (d) — Employees above average

File:

```text
reports/report_employees_above_average.sql
```

The average ticket count among the 11 employees who raised at least one ticket is:

```text
2.727272727272727
```

Expected output:

```text
Aarav Sharma|1|7
Vivaan Rao|7|4
Aditya Menon|9|3
Arjun Reddy|11|7
```

These are exactly four employees.

---

## Report (e) — Asset type overlap

File:

```text
reports/report_asset_type_overlap.sql
```

### UNION result

The UNION returns exactly 8 distinct asset IDs:

```text
1
2
3
4
5
6
8
11
```

### EXCEPT result

The EXCEPT operation returns exactly:

```text
3
4
8
11
```

The EXCEPT result represents incident-ticket assets that do not also have maintenance tickets.

---

## Report (f) — Ticket type/status HAVING report

File:

```text
reports/report_type_status_having.sql
```

The query uses:

```sql
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
```

Expected output:

```text
incident|Open|3
service_request|Closed|4
service_request|InProgress|3
service_request|Open|7
service_request|Resolved|4
```

Exactly five rows are returned.

---

## Report (g) — Employee ranking using RANK()

File:

```text
reports/report_employee_rank_window.sql
```

The report uses:

```sql
RANK() OVER (ORDER BY ticket_count DESC)
```

Expected output:

```text
1|Aarav Sharma|7|1
11|Arjun Reddy|7|1
7|Vivaan Rao|4|3
9|Aditya Menon|3|4
6|Meera Iyer|2|5
10|Sara Khan|2|5
2|Isha Verma|1|7
3|Rohan Gupta|1|7
4|Diya Nair|1|7
5|Kabir Singh|1|7
8|Ananya Joshi|1|7
```

Aarav Sharma and Arjun Reddy tie at rank 1. Vivaan Rao receives rank 3 because `RANK()` leaves a gap after the tie.

---

# Task 5 — Indexing and Measurement

The composite index required by the brief is:

```sql
CREATE INDEX idx_tickets_type_status
ON tickets(ticket_type, status);
```

It is documented in:

```text
INDEXING_NOTES.md
```

The measured query is the Task 4(f) query:

```sql
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

## Before the index

Run:

```sql
EXPLAIN QUERY PLAN
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

Measured raw output:

```text
7|0|0|SCAN tickets
9|0|0|USE TEMP B-TREE FOR GROUP BY
```

## Create the index

```sql
CREATE INDEX idx_tickets_type_status
ON tickets(ticket_type, status);
```

## After the index

Run the identical query plan:

```sql
EXPLAIN QUERY PLAN
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

Measured raw output:

```text
7|0|0|SCAN tickets USING COVERING INDEX idx_tickets_type_status
```

The before plan scans the table and builds a temporary B-tree for grouping. The after plan can scan the covering composite index in the required `(ticket_type, status)` order, eliminating the separate temporary GROUP BY structure.

SQLite versions may format the numeric columns slightly differently, but the important plan text is the same.

---

# Part 3 — HLD/LLD & Scale-Readiness Design

The Part 3 design document is:

```text
DESIGN.md
```

It is grounded in the actual files and classes in this repository.

## High-Level Design

The architecture is:

```text
Presentation
    |
Business
    |
Data Access
    |
Database
```

### Presentation layer

The project uses command-line execution through:

```text
engine.py
run_concurrency_experiment.py
README.md
```

There is no browser UI in this project.

### Business layer

The business layer contains:

```text
Ticket
IncidentTicket
ServiceRequestTicket
MaintenanceTicket
Employee
Asset
HelpdeskEngine
```

### Data Access layer

The data-access layer contains:

```text
Repository
reports/*.sql
```

### Database layer

The database layer is defined by:

```text
schema.sql
seed_data.sql
SQLite
```

---

# SOLID Design

`DESIGN.md` gives a class-specific SOLID justification for:

```text
Ticket
IncidentTicket
HelpdeskEngine
Repository
Employee
```

The design uses concrete principles rather than generic statements.

Examples include:

- Ticket — Single Responsibility Principle
- IncidentTicket — Open/Closed Principle
- HelpdeskEngine — Dependency Inversion Principle
- Repository — Single Responsibility Principle
- Employee — Interface Segregation Principle

---

# Mermaid Diagrams

`DESIGN.md` contains two required Mermaid diagrams.

## Class diagram

The class diagram shows:

```text
Ticket
IncidentTicket
ServiceRequestTicket
MaintenanceTicket
HelpdeskEngine
Repository
Employee
Asset
```

It also shows inheritance and associations between employees, assets, and tickets.

## Sequence diagram

The sequence diagram shows:

```text
Employee
    |
HelpdeskEngine
    |
Repository
    |
SQLite
```

and the transactional status-update path:

```text
BEGIN
SELECT old status
UPDATE tickets
INSERT ticket_status_history
COMMIT
```

---

# Scale-Readiness

The design discusses the following project-specific topics.

## Horizontal vs. vertical scaling

The `tickets` table and ticket aggregation reports are identified as the database workload to monitor as ticket volume grows. The Task 4 reports repeatedly aggregate ticket data, and Task 5 measures the composite `(ticket_type, status)` index.

## Load balancing

The design selects:

```text
Least Connection
```

for a future stateless HTTP deployment.

The reason statelessness matters is that persistent ticket and asset state remains in the database, so requests can be served by different application instances without pinning a user's state to one instance.

## Microservices decomposition

The proposed split is:

```text
Asset Management Service
        |
        | owns assets
        |
Ticket Management Service
        |
        | owns tickets and ticket_status_history
```

Asset Management owns the `assets` table as its source of truth. Ticket Management keeps the asset reference needed by tickets.

The main trade-off is that the local SQLite foreign-key transaction cannot span independently deployed services. The design therefore proposes API validation and/or replicated reference data plus events, accepting eventual consistency across the service boundary.

---

# Final Verification Checklist

Before submitting, verify that the public GitHub repository contains at least:

```text
README.md
engine.py
schema.sql
seed_data.sql
repository.py
run_concurrency_experiment.py
reports/
    report_tickets_per_employee_inner.sql
    report_tickets_per_employee_left.sql
    report_asset_ticket_coverage.sql
    report_employees_above_average.sql
    report_asset_type_overlap.sql
    report_type_status_having.sql
    report_employee_rank_window.sql
INDEXING_NOTES.md
DESIGN.md
```

Run:

```bash
python engine.py
```

Then create a fresh database:

```bash
python -c "import sqlite3; c=sqlite3.connect('sentineldesk.db'); c.executescript(open('schema.sql').read()); c.executescript(open('seed_data.sql').read()); c.close()"
```

Run:

```bash
python repository.py
```

Run:

```bash
python run_concurrency_experiment.py
```

Verify:

```text
12 employees
18 assets
30 tickets
50 ticket_status_history rows
```

Verify the Part 2 ticket status distribution:

```text
Open        = 10
InProgress  = 6
Resolved    = 7
Closed      = 7
```

Verify:

```text
service_request + Open = 7
incident + Open        = 3
```

Verify that all seven report files exist.

Verify that `INDEXING_NOTES.md` contains both before-index and after-index `EXPLAIN QUERY PLAN` outputs.

Verify that `DESIGN.md` contains:

```text
HelpdeskEngine
Repository
Ticket
```

in the High-Level Design section.

Verify that `DESIGN.md` contains:

```text
classDiagram
sequenceDiagram
```

inside Mermaid fenced code blocks.

Verify that `DESIGN.md` contains:

```text
Least Connection
```

and the specific Asset Management / Ticket Management microservices split with its consistency trade-off and ownership rule.

---

# Submission

Push all files to the same public GitHub repository:

```text
sentineldesk
```

The submission is the single public GitHub repository link.

The repository contains the code, SQL seed data, seven report files, indexing measurement, design documentation, and this README with setup instructions and reproducible acceptance-criterion outputs.
