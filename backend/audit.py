"""Append-only audit trail at output/audit_trail.json.

The file is a JSON list. Each event is appended under a file lock and the file
is rewritten atomically, so earlier runs are never wiped.
"""

from __future__ import annotations

import fcntl
import itertools
import json
from datetime import datetime, timezone
from typing import Any

from config import AUDIT_TEXT_LIMIT, AUDIT_TRAIL_PATH
from models import AuditEvent


def clip(value: Any, limit: int = AUDIT_TEXT_LIMIT) -> Any:
    """Shorten long strings so one huge tool result cannot bloat the trail."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"... [+{len(value) - limit} chars]"
    return value


class AuditTrail:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._seq = itertools.count(1)

    def log(self, step: str, *, agent: str | None = None, ticket_id: int | None = None,
            depth: int | None = None, parent_agent: str | None = None, **data: Any) -> AuditEvent:
        event = AuditEvent(
            run_id=self.run_id,
            seq=next(self._seq),
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            step=step,
            agent=agent,
            ticket_id=ticket_id,
            depth=depth,
            parent_agent=parent_agent,
            data={k: clip(v) for k, v in data.items()},
        )
        append_event(event.model_dump(mode="json"))
        return event


def append_event(event: dict[str, Any]) -> None:
    AUDIT_TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_TRAIL_PATH.with_name(".audit_trail.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        text = AUDIT_TRAIL_PATH.read_text() if AUDIT_TRAIL_PATH.exists() else ""
        events = json.loads(text) if text.strip() else []
        events.append(event)
        tmp = AUDIT_TRAIL_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(events, indent=2, default=str))
        tmp.replace(AUDIT_TRAIL_PATH)
