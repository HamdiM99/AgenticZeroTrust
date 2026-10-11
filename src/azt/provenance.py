"""Provenance ledger. Labels are attached by the ingestion layer, NEVER by an agent.

Anything not in the ledger is "unknown" and therefore untrusted (default deny).
Known limitation: exact-value matching; it does not follow derived/transformed values.
"""
from __future__ import annotations

import re

from .util import norm_iban

_IBAN_CANDIDATE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")


class Provenance:
    def __init__(self) -> None:
        self._m: dict[str, set[str]] = {}

    def ingest(self, iban: str, origin: str) -> None:
        self._m.setdefault(norm_iban(iban), set()).add(origin)

    def ingest_document(self, text: str, origin: str) -> None:
        """Register every IBAN-looking string in untrusted content with its (untrusted) origin."""
        for cand in _IBAN_CANDIDATE.findall(text):
            self.ingest(cand, origin)

    def origins(self, iban: str) -> set[str]:
        return self._m.get(norm_iban(iban), {"unknown"})
