# sentineldesk
SentinelDesk — An Internal IT Asset and Ticket Management Platform

SentinelDesk is an internal IT asset and ticket management platform designed to replace spreadsheet-based tracking of IT assets and support tickets.

The project is implemented using Python and SQLite. It contains:

- A domain model for employees, assets, and tickets
- An in-memory helpdesk engine
- SQLite database schema and seed data
- Repository and transaction management
- Concurrency experiment
- SQL reporting
- Database indexing analysis
- High-Level Design (HLD)
- Low-Level Design (LLD)
- Scale-readiness documentation

---

# Project Structure

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
│   ├── report1.sql
│   ├── report2.sql
│   └── ...
│
├── INDEXING_NOTES.md
└── DESIGN.md
