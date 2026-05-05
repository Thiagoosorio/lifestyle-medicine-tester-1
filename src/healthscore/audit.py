"""Audit-log sink (architecture_spec.md §11).

The scoring core never opens files / sockets / stdout; it emits one
structured dict per ``engine.compute()`` call to an injected
``AuditSink``. The I/O layer is responsible for durability, retention,
redaction, and PII handling.

Two sinks ship in this module:

    * ``InMemoryAuditSink`` -- collects emitted records on a list,
      useful for tests and for the Sobol harness which captures every
      perturbation's audit blob.
    * ``JSONLAuditSink``    -- appends one JSON object per line to a
      file, the canonical durable format described by §11.

Both are reference implementations; production deployments may swap in
their own ``AuditSink`` (a ``Protocol`` -- see below) without touching
the core.

Pure: ``InMemoryAuditSink`` is pure in-process state; ``JSONLAuditSink``
opens files only on ``emit`` (one append per call).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Protocol


class AuditSink(Protocol):
    """Engine-injected audit channel. Called once per compute() call."""

    def emit(self, record: Mapping[str, Any]) -> None: ...


class InMemoryAuditSink:
    """Reference impl that appends to a list. Useful for tests + harness."""

    __slots__ = ("records",)

    def __init__(self) -> None:
        self.records: list[Mapping[str, Any]] = []

    def emit(self, record: Mapping[str, Any]) -> None:
        # Deep-copy via JSON round-trip so caller mutations after emit()
        # do not retroactively change the recorded audit blob.
        self.records.append(json.loads(json.dumps(record, default=str)))


class JSONLAuditSink:
    """Append one JSON object per line to ``path``. Atomic per emit()."""

    __slots__ = ("path",)

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: Mapping[str, Any]) -> None:
        line = json.dumps(record, default=str, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
