from dataclasses import dataclass

SLA_TARGETS: dict[str, dict[str, int]] = {
    "critical": {"response": 30, "resolve": 240},
    "high": {"response": 60, "resolve": 480},
    "medium": {"response": 240, "resolve": 1440},
    "low": {"response": 480, "resolve": 4320},
}

TICKET_STATUSES = ("new", "open", "in_progress", "resolved", "closed")
PRIORITIES = ("low", "medium", "high", "critical")
CATEGORIES = ("hardware", "software", "network", "access", "other")
ROLES = ("employee", "support", "admin")


@dataclass(frozen=True)
class Transition:
    from_status: str
    to_status: str
    role: str
    allow_owner: bool = False


# role = minimum role allowed: "employee" (any) / "support" / "admin"
TICKET_TRANSITIONS: tuple[Transition, ...] = (
    Transition("new", "open", "support"),
    Transition("new", "closed", "admin"),  # rejected / cancelled stakeholderc
    Transition("new", "in_progress", "support"),
    Transition("new", "resolved", "support"),
    Transition("open", "in_progress", "support"),
    Transition("open", "resolved", "support"),
    Transition("open", "closed", "admin"),
    Transition("in_progress", "resolved", "support"),
    Transition("in_progress", "new", "support"),
    Transition("in_progress", "closed", "admin"),
    Transition("resolved", "closed", "support"),
    Transition("resolved", "open", "employee", allow_owner=True),  # reopen
)

STATUS_RANK = {s: i for i, s in enumerate(TICKET_STATUSES)}

ROLE_RANK = {"employee": 0, "support": 1, "admin": 2}
