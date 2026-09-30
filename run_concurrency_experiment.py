import os
import sqlite3
import tempfile
import threading
import time


def create_isolated_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE tickets (
            ticket_id INTEGER PRIMARY KEY,
            reopen_count INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO tickets(ticket_id, reopen_count) VALUES (1, 0);
        """
    )
    conn.commit()
    conn.close()


def reopen_ticket_naive(conn: sqlite3.Connection, ticket_id: int, barrier: threading.Barrier) -> None:
    """Read, wait, then write using independent autocommit statements."""
    row = conn.execute(
        "SELECT reopen_count FROM tickets WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()
    current = row[0]

    # Both workers have now observed the same starting value.
    barrier.wait()
    time.sleep(0.05)

    conn.execute(
        "UPDATE tickets SET reopen_count = ? WHERE ticket_id = ?",
        (current + 1, ticket_id),
    )


def reopen_ticket_safe(conn: sqlite3.Connection, ticket_id: int, barrier: threading.Barrier) -> None:
    """Serialize the read-modify-write using SQLite's BEGIN IMMEDIATE lock."""
    barrier.wait()

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT reopen_count FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()
        current = row[0]

        time.sleep(0.05)

        conn.execute(
            "UPDATE tickets SET reopen_count = ? WHERE ticket_id = ?",
            (current + 1, ticket_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def run_trial(worker_function) -> int:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        create_isolated_db(db_path)

        barrier = threading.Barrier(2)
        errors = []

        def worker() -> None:
            conn = sqlite3.connect(db_path, timeout=5.0, isolation_level=None)
            try:
                worker_function(conn, 1, barrier)
            except Exception as exc:
                errors.append(exc)
            finally:
                conn.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        if errors:
            raise RuntimeError(f"Worker error: {errors}")

        conn = sqlite3.connect(db_path)
        value = conn.execute(
            "SELECT reopen_count FROM tickets WHERE ticket_id = 1"
        ).fetchone()[0]
        conn.close()
        return value

    finally:
        os.remove(db_path)


def main() -> None:
    naive_results = [run_trial(reopen_ticket_naive) for _ in range(5)]
    safe_results = [run_trial(reopen_ticket_safe) for _ in range(5)]

    print("Naive final reopen_count values:")
    for i, value in enumerate(naive_results, 1):
        print(f"Trial {i}: {value}")

    print("\nSafe (BEGIN IMMEDIATE) final reopen_count values:")
    for i, value in enumerate(safe_results, 1):
        print(f"Trial {i}: {value}")

    assert all(value == 1 for value in naive_results), naive_results
    assert all(value == 2 for value in safe_results), safe_results

    print("\nPASS: naive version reproduced the lost-update result 1 in all 5 trials.")
    print("PASS: BEGIN IMMEDIATE version produced the correct result 2 in all 5 trials.")


if __name__ == "__main__":
    main()
