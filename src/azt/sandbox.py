"""Ready-made world used by tests, the demo and the evaluation harness (fictional data only)."""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from .approval import ApprovalService
from .audit import AuditLog
from .bank import CoreBank
from .gateway import ToolGateway
from .identity import IdentityService
from .provenance import Provenance

SRC = "FR76ACCOUNTBANK0000001"
GOOD = "FR7630001007941234567890185"      # verified beneficiary (registry)
GOOD2 = "FR7630004000031234567890143"     # another verified beneficiary (not the task's payee)
ATTACKER = "FR76ATTACKER00000000000001"   # never in the registry


@dataclass
class World:
    audit: AuditLog
    ids: IdentityService
    prov: Provenance
    approvals: ApprovalService
    bank: CoreBank
    gw: ToolGateway

    def token(self, agent: str = "agent:payment", *, beneficiary: str = GOOD, source: str = SRC,
              currency: str = "EUR", max_cents: int = 50_000, task: str = "pay-invoice-42") -> str:
        return self.ids.issue(agent, task, max_amount_cents=max_cents, beneficiary=beneficiary,
                              source=source, currency=currency)


def build_world() -> World:
    audit, ids, prov = AuditLog(), IdentityService(), Provenance()
    approvals = ApprovalService({"human:marie": secrets.token_bytes(32), "human:karim": secrets.token_bytes(32)})
    credential = secrets.token_hex(16)
    bank = CoreBank(credential)
    ids.register("agent:kyc", ["kyc:read"])
    ids.register("agent:payment", ["transfer:create"])
    for iban in (GOOD, GOOD2):
        prov.ingest(iban, "registry")
    gw = ToolGateway(ids, prov, approvals, audit, bank, credential)
    return World(audit, ids, prov, approvals, bank, gw)


def intent(to: str = GOOD, amount_cents: int = 50_000, currency: str = "EUR") -> dict:
    return {"from": SRC, "to_iban": to, "amount_cents": amount_cents, "currency": currency}
