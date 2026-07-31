"""Author-defined tool registry — schemas + execute (no model-created tools)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from src.tools.store import (
    ALLOWED_SEVERITIES,
    ALLOWED_TEAMS,
    TicketStore,
    normalize_severity,
    normalize_team,
)

# OpenAI Chat Completions tools format
ToolSchema = dict[str, Any]
ToolHandler = Callable[[TicketStore, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolResult:
    """Structured result from registry.execute — never raises for business errors."""

    ok: bool
    tool: str
    data: dict[str, Any] | None = None
    error: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": self.ok, "tool": self.tool}
        if self.data is not None:
            out["data"] = self.data
        if self.error is not None:
            out["error"] = self.error
        if self.error_code is not None:
            out["error_code"] = self.error_code
        return out


def _require_str(args: dict[str, Any], key: str) -> str:
    if key not in args or args[key] is None:
        raise ValueError(f"Missing required argument: {key}")
    val = args[key]
    if not isinstance(val, str):
        raise ValueError(f"Argument '{key}' must be a string")
    text = val.strip()
    if not text:
        raise ValueError(f"Argument '{key}' must be non-empty")
    return text


def _optional_str(args: dict[str, Any], key: str) -> str | None:
    if key not in args or args[key] is None:
        return None
    val = args[key]
    if not isinstance(val, str):
        raise ValueError(f"Argument '{key}' must be a string")
    text = val.strip()
    return text or None


def _tool_search_known_issues(store: TicketStore, args: dict[str, Any]) -> dict[str, Any]:
    query = _require_str(args, "query")
    hits = store.search_known_issues(query)
    return {
        "query": query,
        "count": len(hits),
        "issues": [h.to_dict() for h in hits],
    }


def _tool_create_bug(store: TicketStore, args: dict[str, Any]) -> dict[str, Any]:
    title = _require_str(args, "title")
    severity_raw = _require_str(args, "severity")
    description = _require_str(args, "description")
    severity = normalize_severity(severity_raw)
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(
            f"Invalid severity '{severity_raw}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_SEVERITIES))}"
        )
    bug = store.add_bug(title=title, severity=severity, description=description)
    return {"bug": bug.to_dict(), "bug_id": bug.bug_id}


def _tool_assign_owner(store: TicketStore, args: dict[str, Any]) -> dict[str, Any]:
    bug_id = _require_str(args, "bug_id")
    team_raw = _require_str(args, "team")
    team = normalize_team(team_raw)
    if team not in ALLOWED_TEAMS:
        raise ValueError(
            f"Invalid team '{team_raw}'. Allowed: {', '.join(sorted(ALLOWED_TEAMS))}"
        )
    bug = store.assign_bug(bug_id, team)
    if bug is None:
        raise ValueError(f"Unknown bug_id: {bug_id}")
    return {"bug": bug.to_dict(), "bug_id": bug.bug_id, "team": team}


def _tool_lookup_user(store: TicketStore, args: dict[str, Any]) -> dict[str, Any]:
    email = _require_str(args, "email")
    user = store.lookup_user(email)
    if user is None:
        return {"found": False, "email": email, "user": None}
    return {"found": True, "email": email, "user": user.to_dict()}


def _tool_list_open_bugs(store: TicketStore, args: dict[str, Any]) -> dict[str, Any]:
    severity = _optional_str(args, "severity")
    if severity is not None:
        sev = normalize_severity(severity)
        if sev not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{severity}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_SEVERITIES))}"
            )
        severity = sev
    bugs = store.list_bugs(severity=severity)
    return {
        "count": len(bugs),
        "severity_filter": severity,
        "bugs": [b.to_dict() for b in bugs],
    }


# name -> (description, parameters JSON schema, handler)
_TOOL_DEFS: dict[str, tuple[str, dict[str, Any], ToolHandler]] = {
    "search_known_issues": (
        "Search the internal known-issues knowledge base for related problems.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords (e.g. login chrome deploy)",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        _tool_search_known_issues,
    ),
    "create_bug": (
        "Create a new bug ticket in the QA tracking system. Returns a bug_id.",
        {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short bug title",
                },
                "severity": {
                    "type": "string",
                    "description": "Severity: low|medium|high|critical|p1|p2|p3|p4",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description for engineers",
                },
            },
            "required": ["title", "severity", "description"],
            "additionalProperties": False,
        },
        _tool_create_bug,
    ),
    "assign_owner": (
        "Assign an existing bug to a team. Requires a real bug_id from create_bug.",
        {
            "type": "object",
            "properties": {
                "bug_id": {
                    "type": "string",
                    "description": "Bug id such as BUG-1001",
                },
                "team": {
                    "type": "string",
                    "description": "Team: web|mobile|backend|qa|platform|infra",
                },
            },
            "required": ["bug_id", "team"],
            "additionalProperties": False,
        },
        _tool_assign_owner,
    ),
    "lookup_user": (
        "Look up a user by email for assignment context.",
        {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User email address",
                }
            },
            "required": ["email"],
            "additionalProperties": False,
        },
        _tool_lookup_user,
    ),
    "list_open_bugs": (
        "List open bugs, optionally filtered by severity. Does not create tickets.",
        {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "Optional severity filter",
                }
            },
            "required": [],
            "additionalProperties": False,
        },
        _tool_list_open_bugs,
    ),
}

MVP_TOOL_NAMES = tuple(_TOOL_DEFS.keys())


class ToolRegistry:
    """
    Fixed author-defined tools. Does not register tools from model output.
    """

    def __init__(self, store: TicketStore | None = None) -> None:
        self.store = store or TicketStore()

    def names(self) -> list[str]:
        return list(MVP_TOOL_NAMES)

    def has_tool(self, name: str) -> bool:
        return name in _TOOL_DEFS

    def tool_schemas(self) -> list[ToolSchema]:
        """OpenAI-compatible `tools` list for chat.completions."""
        tools: list[ToolSchema] = []
        for name, (description, parameters, _) in _TOOL_DEFS.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters,
                    },
                }
            )
        return tools

    def execute(self, name: str, args: dict[str, Any] | None = None) -> ToolResult:
        """
        Execute a registered tool. Unknown tools and validation errors
        return ToolResult(ok=False) — no dynamic registration.
        """
        args = args or {}
        if not isinstance(args, dict):
            return ToolResult(
                ok=False,
                tool=str(name),
                error="Arguments must be a JSON object",
                error_code="INVALID_ARGS",
            )
        if name not in _TOOL_DEFS:
            return ToolResult(
                ok=False,
                tool=str(name),
                error=f"Unknown tool: {name}",
                error_code="UNKNOWN_TOOL",
            )
        _, _, handler = _TOOL_DEFS[name]
        try:
            data = handler(self.store, args)
            return ToolResult(ok=True, tool=name, data=data)
        except ValueError as exc:
            return ToolResult(
                ok=False,
                tool=name,
                error=str(exc),
                error_code="VALIDATION_ERROR",
            )
        except Exception as exc:  # pragma: no cover — defensive
            return ToolResult(
                ok=False,
                tool=name,
                error=f"Tool execution failed: {exc}",
                error_code="EXECUTION_ERROR",
            )

    def snapshot(self) -> dict[str, Any]:
        return self.store.snapshot()

    def reset(self) -> None:
        self.store.reset()


def default_registry() -> ToolRegistry:
    return ToolRegistry()
