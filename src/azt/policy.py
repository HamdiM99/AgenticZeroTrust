"""Policy Decision Point backed by Cedar (via cedarpy). Rules live in policies/*.cedar, not in Python."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import cedarpy

DEFAULT_DIR = Path(os.environ.get("AZT_POLICY_DIR", Path(__file__).resolve().parents[2] / "policies"))

REASON_TEXT = {
    "forbid-unverified-beneficiary": "beneficiary not verified by the registry (untrusted provenance)",
    "forbid-sanctioned": "beneficiary is sanctioned",
    "forbid-beneficiary-not-in-task": "beneficiary differs from the one bound to this task",
    "forbid-over-task-cap": "amount exceeds the remaining budget bound to this task",
    "forbid-source-not-in-task": "source account differs from the one bound to this task",
    "forbid-currency-not-in-task": "currency differs from the one bound to this task",
    "forbid-hard-cap": "amount exceeds the absolute hard cap",
    "forbid-nonpositive-amount": "amount must be positive",
    "forbid-velocity": "too many transfers in the last minute",
    "forbid-kill-switch": "kill-switch is active",
    "no-permit": "no policy permits this action (missing scope or approval)",
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    policies: tuple[str, ...]  # ids of the determining policies

    @property
    def reason(self) -> str:
        return "; ".join(REASON_TEXT.get(p, p) for p in self.policies) or REASON_TEXT["no-permit"]


class CedarPDP:
    def __init__(self, policy_dir: Path = DEFAULT_DIR) -> None:
        self.policies = (policy_dir / "transfer.cedar").read_text()
        self.schema = (policy_dir / "schema.cedarschema").read_text()
        res = cedarpy.validate_policies(self.policies, self.schema)
        if not res.validation_passed:
            raise ValueError(f"Cedar policies fail schema validation: {[str(e) for e in res.errors]}")
        self._ids = re.findall(r'@id\("([^"]+)"\)', self.policies)

    def _name(self, pid: str) -> str:
        m = re.fullmatch(r"policy(\d+)", pid)
        return self._ids[int(m.group(1))] if m and int(m.group(1)) < len(self._ids) else pid

    def decide(self, agent: str, scopes: list[str], beneficiary: dict, context: dict) -> Decision:
        entities = [
            {"uid": {"type": "Agent", "id": agent}, "attrs": {"scopes": list(scopes)}, "parents": []},
            {"uid": {"type": "Beneficiary", "id": beneficiary["iban"]}, "attrs": beneficiary, "parents": []},
        ]
        request = {
            "principal": f'Agent::"{agent}"', "action": 'Action::"transfer"',
            "resource": f'Beneficiary::"{beneficiary["iban"]}"', "context": context,
        }
        res = cedarpy.is_authorized(request, self.policies, entities, self.schema)
        if res.diagnostics.errors:  # evaluation error => fail closed
            return Decision(False, ("evaluation-error",))
        return Decision(res.allowed, tuple(sorted(self._name(p) for p in res.diagnostics.reasons)))
