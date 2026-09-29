from abc import ABC, abstractmethod
from datetime import datetime
import sqlite3


# ============================================================
# Ticket Domain Model
# ============================================================

class Ticket(ABC):
    """
    Abstract base class representing a helpdesk ticket.

    Ticket cannot be instantiated directly because
    resolution_checklist() is an abstract method.
    """

    def __init__(
        self,
        ticket_id: int,
        asset_id: int | None,
        raised_by: int,
        priority: str,
        status: str,
        created_at: str,
        resolved_at: str | None
    ):
        self.ticket_id = ticket_id
        self.asset_id = asset_id
        self.raised_by = raised_by
        self.priority = priority
        self.status = status
        self.created_at = created_at
        self.resolved_at = resolved_at

    @abstractmethod
    def resolution_checklist(self) -> list[str]:
        """
        Return the resolution checklist for this
        particular type of ticket.
        """
        pass

    def age_in_days(self, reference_date: str) -> int:
        """
        Calculate the number of days between created_at
        and the supplied reference date.

        Both dates use YYYY-MM-DD format.
        """

        created_date = datetime.strptime(
            self.created_at,
            "%Y-%m-%d"
        ).date()

        reference = datetime.strptime(
            reference_date,
            "%Y-%m-%d"
        ).date()

        return (reference - created_date).days


# ============================================================
# Incident Ticket
# ============================================================

class IncidentTicket(Ticket):
    """
    Represents an incident such as a system failure,
    outage, hardware problem, or unexpected error.
    """

    def resolution_checklist(self) -> list[str]:
        return [
            "Confirm and reproduce the incident",
            "Perform triage and identify the affected service",
            "Identify the root cause",
            "Apply the required corrective action",
            "Verify the fix and affected system",
            "Document the incident and resolution"
        ]


# ============================================================
# Service Request Ticket
# ============================================================

class ServiceRequestTicket(Ticket):
    """
    Represents a service request such as software access,
    account provisioning, or equipment request.
    """

    def resolution_checklist(self) -> list[str]:
        return [
            "Validate the service request",
            "Confirm required approval",
            "Verify requester eligibility",
            "Provision or perform the requested service",
            "Verify that the request has been completed",
            "Record completion details"
        ]


# ============================================================
# Maintenance Ticket
# ============================================================

class MaintenanceTicket(Ticket):
    """
    Represents planned maintenance work such as updates,
    servicing, scheduled downtime, or preventive maintenance.
    """

    def resolution_checklist(self) -> list[str]:
        return [
            "Confirm the maintenance requirement",
            "Schedule an approved maintenance window",
            "Notify affected users or teams",
            "Perform the maintenance or downtime activity",
            "Verify system availability after maintenance",
            "Record maintenance and verification details"
        ]


# ============================================================
# Employee
# ============================================================

class Employee:
    """
    Represents an employee in the organization.
    """

    def __init__(
        self,
        emp_id: int,
        name: str,
        department: str,
        role: str
    ):
        self.emp_id = emp_id
        self.name = name
        self.department = department
        self.role = role

    def __repr__(self) -> str:
        return (
            f"Employee("
            f"emp_id={self.emp_id}, "
            f"name={self.name!r}, "
            f"department={self.department!r}, "
            f"role={self.role!r})"
        )


# ============================================================
# Asset
# ============================================================

class Asset:
    """
    Represents an IT asset assigned to an employee.
    """

    def __init__(
        self,
        asset_id: int,
        asset_tag: str,
        category: str,
        purchase_date: str,
        assigned_to: int | None
    ):
        self.asset_id = asset_id
        self.asset_tag = asset_tag
        self.category = category
        self.purchase_date = purchase_date
        self.assigned_to = assigned_to

    def __repr__(self) -> str:
        return (
            f"Asset("
            f"asset_id={self.asset_id}, "
            f"asset_tag={self.asset_tag!r}, "
            f"category={self.category!r}, "
            f"purchase_date={self.purchase_date!r}, "
            f"assigned_to={self.assigned_to})"
        )


# ============================================================
# Helpdesk Engine
# ============================================================

class HelpdeskEngine:
    """
    In-memory engine for employees, assets, and tickets.

    Data is loaded from the SQLite database created in Part 2.
    """

    def __init__(self):
        self.employees_by_id: dict[int, Employee] = {}
        self.assets_by_id: dict[int, Asset] = {}
        self.tickets_by_status: dict[str, list[Ticket]] = {}

        # Distinct ticket type values encountered while loading.
        self.ticket_type_seen: set[str] = set()

        # Number of tickets grouped by ticket type and status.
        self.count_by_type_status: dict[tuple[str, str], int] = {}

    # --------------------------------------------------------
    # Database Loading
    # --------------------------------------------------------

    def load_from_db(self, db_path: str) -> None:
        """
        Load employees, assets, and tickets from a SQLite database.

        Employees are stored in employees_by_id.
        Assets are stored in assets_by_id.
        Tickets are grouped by status.

        The correct Ticket subclass is created according
        to the ticket_type column.
        """

        # Clear previous data before loading.
        self.employees_by_id.clear()
        self.assets_by_id.clear()
        self.tickets_by_status.clear()
        self.ticket_type_seen.clear()
        self.count_by_type_status.clear()

        connection = sqlite3.connect(db_path)

        # Allow database columns to be accessed by name.
        connection.row_factory = sqlite3.Row

        try:
            cursor = connection.cursor()

            # ====================================================
            # Load Employees
            # ====================================================

            cursor.execute(
                """
                SELECT
                    emp_id,
                    name,
                    department,
                    role
                FROM employees
                """
            )

            employee_rows = cursor.fetchall()

            for row in employee_rows:
                employee = Employee(
                    emp_id=int(row["emp_id"]),
                    name=row["name"],
                    department=row["department"],
                    role=row["role"]
                )

                self.employees_by_id[employee.emp_id] = employee

            # ====================================================
            # Load Assets
            # ====================================================

            cursor.execute(
                """
                SELECT
                    asset_id,
                    asset_tag,
                    category,
                    purchase_date,
                    assigned_to
                FROM assets
                """
            )

            asset_rows = cursor.fetchall()

            for row in asset_rows:
                assigned_to = row["assigned_to"]

                if assigned_to is not None:
                    assigned_to = int(assigned_to)

                asset = Asset(
                    asset_id=int(row["asset_id"]),
                    asset_tag=row["asset_tag"],
                    category=row["category"],
                    purchase_date=row["purchase_date"],
                    assigned_to=assigned_to
                )

                self.assets_by_id[asset.asset_id] = asset

            # ====================================================
            # Load Tickets
            # ====================================================

            cursor.execute(
                """
                SELECT
                    ticket_id,
                    asset_id,
                    raised_by,
                    priority,
                    status,
                    created_at,
                    resolved_at,
                    ticket_type
                FROM tickets
                """
            )

            ticket_rows = cursor.fetchall()

            for row in ticket_rows:

                ticket_type = str(
                    row["ticket_type"]
                ).strip().lower()

                # ------------------------------------------------
                # Create the correct concrete Ticket subclass.
                # Ticket itself is NEVER instantiated here.
                # ------------------------------------------------

                if ticket_type == "incident":

                    ticket = IncidentTicket(
                        ticket_id=int(row["ticket_id"]),
                        asset_id=(
                            int(row["asset_id"])
                            if row["asset_id"] is not None
                            else None
                        ),
                        raised_by=int(row["raised_by"]),
                        priority=row["priority"],
                        status=row["status"],
                        created_at=row["created_at"],
                        resolved_at=row["resolved_at"]
                    )

                elif ticket_type == "service_request":

                    ticket = ServiceRequestTicket(
                        ticket_id=int(row["ticket_id"]),
                        asset_id=(
                            int(row["asset_id"])
                            if row["asset_id"] is not None
                            else None
                        ),
                        raised_by=int(row["raised_by"]),
                        priority=row["priority"],
                        status=row["status"],
                        created_at=row["created_at"],
                        resolved_at=row["resolved_at"]
                    )

                elif ticket_type == "maintenance":

                    ticket = MaintenanceTicket(
                        ticket_id=int(row["ticket_id"]),
                        asset_id=(
                            int(row["asset_id"])
                            if row["asset_id"] is not None
                            else None
                        ),
                        raised_by=int(row["raised_by"]),
                        priority=row["priority"],
                        status=row["status"],
                        created_at=row["created_at"],
                        resolved_at=row["resolved_at"]
                    )

                else:
                    raise ValueError(
                        f"Unknown ticket_type: {row['ticket_type']}"
                    )

                # ------------------------------------------------
                # Store ticket under its status.
                # ------------------------------------------------

                status = ticket.status

                if status not in self.tickets_by_status:
                    self.tickets_by_status[status] = []

                self.tickets_by_status[status].append(ticket)

                # ------------------------------------------------
                # Record the ticket type.
                # ------------------------------------------------

                self.ticket_type_seen.add(ticket_type)

                # ------------------------------------------------
                # Count ticket type + status combination.
                # ------------------------------------------------

                key = (ticket_type, status)

                self.count_by_type_status[key] = (
                    self.count_by_type_status.get(key, 0) + 1
                )

        finally:
            connection.close()


# ============================================================
# Notification Function
# ============================================================

def notify(ticket: Ticket) -> list[str]:
    """
    Return the resolution checklist for a ticket.

    Ticket is an abstract base class and declares
    resolution_checklist(). Therefore every concrete
    Ticket object passed to this function is guaranteed
    to implement that method.

    If Ticket were an ordinary duck-typed class instead,
    an object missing resolution_checklist() might not fail
    until this function was called, causing AttributeError.
    """

    return ticket.resolution_checklist()


# ============================================================
# Basic Part 1 Tests
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Test 1: Ticket cannot be instantiated directly.
    # --------------------------------------------------------

    try:
        Ticket(
            ticket_id=1,
            asset_id=None,
            raised_by=1,
            priority="High",
            status="Open",
            created_at="2026-07-02",
            resolved_at=None
        )

        print("ERROR: Ticket should not be directly instantiable.")

    except TypeError:
        print("PASS: Ticket is abstract and cannot be instantiated.")

    # --------------------------------------------------------
    # Test 2: age_in_days()
    # --------------------------------------------------------

    incident = IncidentTicket(
        ticket_id=1,
        asset_id=1,
        raised_by=1,
        priority="High",
        status="Open",
        created_at="2026-07-02",
        resolved_at=None
    )

    assert incident.age_in_days("2026-07-10") == 8

    print("PASS: age_in_days() returned 8.")

    # --------------------------------------------------------
    # Test 3: Three different Ticket subclasses.
    # --------------------------------------------------------

    service_request = ServiceRequestTicket(
        ticket_id=2,
        asset_id=None,
        raised_by=2,
        priority="Medium",
        status="Open",
        created_at="2026-07-02",
        resolved_at=None
    )

    maintenance = MaintenanceTicket(
        ticket_id=3,
        asset_id=2,
        raised_by=3,
        priority="Low",
        status="Open",
        created_at="2026-07-02",
        resolved_at=None
    )

    assert len(incident.resolution_checklist()) > 0
    assert len(service_request.resolution_checklist()) > 0
    assert len(maintenance.resolution_checklist()) > 0

    assert (
        incident.resolution_checklist()
        != service_request.resolution_checklist()
    )

    assert (
        service_request.resolution_checklist()
        != maintenance.resolution_checklist()
    )

    print("PASS: All Ticket subclasses provide distinct checklists.")

    # --------------------------------------------------------
    # Test 4: notify()
    # --------------------------------------------------------

    assert isinstance(notify(incident), list)
    assert isinstance(notify(service_request), list)
    assert isinstance(notify(maintenance), list)

    print("PASS: notify() works for all Ticket subclasses.")

    print("\nPart 1 basic tests completed successfully.")
