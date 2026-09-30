import sqlite3
from typing import Optional


class Repository:
    """Transactional write operations for SentinelDesk."""

    def update_ticket_status(
        self,
        conn: sqlite3.Connection,
        ticket_id: int,
        new_status: str,
    ) -> None:
        """
        Atomically update a ticket's status and append its status-history row.

        Both writes occur in one explicit transaction. Any exception causes a
        rollback, so the ticket update and history insert cannot commit alone.
        """
        try:
            conn.execute("BEGIN")
            row = conn.execute(
                "SELECT status FROM tickets WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Ticket {ticket_id} does not exist")

            old_status = row[0]

            conn.execute(
                "UPDATE tickets SET status = ? WHERE ticket_id = ?",
                (new_status, ticket_id),
            )

            conn.execute(
                """
                INSERT INTO ticket_status_history
                    (ticket_id, old_status, new_status, changed_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (ticket_id, old_status, new_status),
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise


def atomicity_test() -> None:
    """Demonstrate one successful transaction and one rolled-back failure."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        """
        CREATE TABLE employees (
            emp_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE assets (
            asset_id INTEGER PRIMARY KEY,
            asset_tag TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            purchase_date TEXT NOT NULL,
            assigned_to INTEGER REFERENCES employees(emp_id)
        );

        CREATE TABLE tickets (
            ticket_id INTEGER PRIMARY KEY,
            asset_id INTEGER REFERENCES assets(asset_id),
            raised_by INTEGER NOT NULL REFERENCES employees(emp_id),
            ticket_type TEXT NOT NULL CHECK (
                ticket_type IN ('incident','service_request','maintenance')
            ),
            priority TEXT NOT NULL CHECK (
                priority IN ('Low','Medium','High','Critical')
            ),
            status TEXT NOT NULL CHECK (
                status IN ('Open','InProgress','Resolved','Closed')
            ),
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            reopen_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE ticket_status_history (
            history_id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TEXT NOT NULL
        );

        INSERT INTO employees VALUES
            (1, 'Test Employee', 'IT Support', 'Support Technician');

        INSERT INTO tickets
            (ticket_id, raised_by, ticket_type, priority, status, created_at)
        VALUES
            (1, 1, 'incident', 'Low', 'Open', '2026-09-01');
        """
    )

    repo = Repository()

    before = conn.execute(
        "SELECT status, (SELECT COUNT(*) FROM ticket_status_history) "
        "FROM tickets WHERE ticket_id = 1"
    ).fetchone()
    print("Before successful call:", before)

    repo.update_ticket_status(conn, 1, "Resolved")

    after_success = conn.execute(
        "SELECT status, (SELECT COUNT(*) FROM ticket_status_history) "
        "FROM tickets WHERE ticket_id = 1"
    ).fetchone()
    print("After successful call:", after_success)

    before_failure = after_success

    try:
        repo.update_ticket_status(conn, 1, "Cancelled")
    except sqlite3.IntegrityError as exc:
        print("Expected failure:", exc)

    after_failure = conn.execute(
        "SELECT status, (SELECT COUNT(*) FROM ticket_status_history) "
        "FROM tickets WHERE ticket_id = 1"
    ).fetchone()
    print("Before failing call:", before_failure)
    print("After failing call:", after_failure)

    assert after_success == ("Resolved", 1)
    assert after_failure == before_failure

    print("PASS: successful call changed one ticket and added one history row.")
    print("PASS: failed call changed zero rows in either table.")
    print("Atomicity test completed successfully.")

    conn.close()


if __name__ == "__main__":
    atomicity_test()
