"""Append-only, hash-chained audit log with tokenised PII."""
from __future__ import annotations

import json
import secrets

from .util import canon, h, sign


class AuditLog:
    def __init__(self) -> None:
        self.entries: list[dict] = []
        self._pii_key = secrets.token_bytes(32)

    def tok(self, value: object) -> str:
        """Tokenise PII so logs never contain raw IBANs (stable per log instance)."""
        return "tok_" + sign(self._pii_key, str(value))[:10]

    def append(self, event: str, **data: object) -> None:
        prev = self.entries[-1]["hash"] if self.entries else "GENESIS"
        body = {"i": len(self.entries), "event": event, "data": data, "prev": prev}
        body["hash"] = h(canon(body))
        self.entries.append(body)

    def verify(self) -> tuple[bool, int | None]:
        """Return (ok, index_of_first_broken_entry)."""
        prev = "GENESIS"
        for e in self.entries:
            body = {k: v for k, v in e.items() if k != "hash"}
            if e["prev"] != prev or h(canon(body)) != e["hash"]:
                return False, e["i"]
            prev = e["hash"]
        return True, None

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e, sort_keys=True) for e in self.entries)
