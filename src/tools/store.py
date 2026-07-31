"""In-memory side-effect store for the QA ticket triage domain."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


ALLOWED_SEVERITIES = frozenset(
    {"low", "medium", "high", "critical", "p1", "p2", "p3", "p4"}
)

ALLOWED_TEAMS = frozenset({"web", "mobile", "backend", "qa", "platform", "infra"})


@dataclass
class Bug:
    bug_id: str
    title: str
    severity: str
    description: str
    team: str | None = None
    status: str = "open"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class User:
    email: str
    name: str
    team: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnownIssue:
    issue_id: str
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_severity(value: str) -> str:
    return value.strip().lower()


def normalize_team(value: str) -> str:
    return value.strip().lower()


class TicketStore:
    """Observable store for bugs, users, and known issues."""

    def __init__(self) -> None:
        self._bugs: dict[str, Bug] = {}
        self._users: dict[str, User] = {}
        self._known_issues: list[KnownIssue] = []
        self._next_bug_num: int = 1000
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        self._users = {
            "alice@example.com": User(
                email="alice@example.com", name="Alice Chen", team="web"
            ),
            "bob@example.com": User(
                email="bob@example.com", name="Bob Diaz", team="backend"
            ),
            "cara@example.com": User(
                email="cara@example.com", name="Cara Ng", team="qa"
            ),
        }
        self._known_issues = [
            KnownIssue(
                issue_id="KI-10",
                title="Chrome login flake after deploy",
                summary="Intermittent login failures on Chrome when session cookies rotate post-deploy.",
                tags=["login", "chrome", "deploy"],
            ),
            KnownIssue(
                issue_id="KI-11",
                title="iOS push notification delay",
                summary="Push delivery can lag up to 5 minutes on iOS 17.",
                tags=["ios", "notifications"],
            ),
            KnownIssue(
                issue_id="KI-12",
                title="Cart total rounding",
                summary="Edge case rounding on multi-currency carts.",
                tags=["cart", "ecommerce"],
            ),
        ]

    def reset(self) -> None:
        """Clear bugs and reset id counter; re-seed users/KB."""
        self._bugs.clear()
        self._next_bug_num = 1000
        self._seed_defaults()

    def next_bug_id(self) -> str:
        self._next_bug_num += 1
        return f"BUG-{self._next_bug_num}"

    def add_bug(self, title: str, severity: str, description: str) -> Bug:
        bug = Bug(
            bug_id=self.next_bug_id(),
            title=title,
            severity=severity,
            description=description,
        )
        self._bugs[bug.bug_id] = bug
        return bug

    def get_bug(self, bug_id: str) -> Bug | None:
        return self._bugs.get(bug_id)

    def assign_bug(self, bug_id: str, team: str) -> Bug | None:
        bug = self._bugs.get(bug_id)
        if bug is None:
            return None
        bug.team = team
        return bug

    def list_bugs(self, severity: str | None = None) -> list[Bug]:
        bugs = list(self._bugs.values())
        if severity is not None:
            sev = normalize_severity(severity)
            bugs = [b for b in bugs if b.severity == sev]
        return sorted(bugs, key=lambda b: b.bug_id)

    def lookup_user(self, email: str) -> User | None:
        key = email.strip().lower()
        # store keys are already lowercase emails
        for user in self._users.values():
            if user.email.lower() == key:
                return user
        return None

    def search_known_issues(self, query: str, limit: int = 5) -> list[KnownIssue]:
        q = query.strip().lower()
        if not q:
            return []
        hits: list[tuple[int, KnownIssue]] = []
        for issue in self._known_issues:
            hay = " ".join(
                [issue.title, issue.summary, " ".join(issue.tags)]
            ).lower()
            score = 0
            for token in q.split():
                if token in hay:
                    score += 1
            if score:
                hits.append((score, issue))
        hits.sort(key=lambda x: (-x[0], x[1].issue_id))
        return [issue for _, issue in hits[:limit]]

    def snapshot(self) -> dict[str, Any]:
        """Deep-copyable view for scoring / console inspection."""
        return {
            "bugs": {bid: bug.to_dict() for bid, bug in sorted(self._bugs.items())},
            "users": {email: user.to_dict() for email, user in sorted(self._users.items())},
            "known_issues": [ki.to_dict() for ki in self._known_issues],
            "bug_count": len(self._bugs),
        }

    def clone_snapshot(self) -> dict[str, Any]:
        return deepcopy(self.snapshot())
