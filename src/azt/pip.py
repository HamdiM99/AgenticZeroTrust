"""Policy Information Point: deterministic attribute sources fed to the PDP (not LLM-derived)."""
from __future__ import annotations

from .util import norm_iban


class SanctionsList:
    def __init__(self, countries: set[str] | None = None, ibans: set[str] | None = None) -> None:
        self.countries = countries or {"KP", "IR"}
        self.ibans = {norm_iban(i) for i in (ibans or set())}

    def is_sanctioned(self, iban: str) -> bool:
        n = norm_iban(iban)
        return n[:2] in self.countries or n in self.ibans
