"""Tool Gateway: the Policy Enforcement Point. The only component holding core-banking credentials.

Agents submit INTENTS; this component authenticates, validates the schema, gathers deterministic
attributes (provenance, sanctions, velocity), asks the Cedar PDP, and only then executes.
No LLM is consulted at any point of this path.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum

from .approval import ApprovalService, intent_hash
from .audit import AuditLog
from .bank import CoreBank
from .identity import IdentityService
from .pip import SanctionsList
from .policy import CedarPDP
from .provenance import Provenance
from .util import IBAN_RE, canonical_intent

ALLOWED_CURRENCIES = {"EUR", "TND"}
INTENT_KEYS = {"from", "to_iban", "amount_cents", "currency"}


class Status(str, Enum):
    EXECUTED = "EXECUTED"
    DENIED = "DENIED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


@dataclass(frozen=True)
class Result:
    status: Status
    reason: str
    policies: tuple[str, ...] = ()
    intent_hash: str | None = None


@dataclass
class ToolGateway:
    ids: IdentityService
    prov: Provenance
    approvals: ApprovalService
    audit: AuditLog
    bank: CoreBank
    credential: str
    pdp: CedarPDP = field(default_factory=CedarPDP)
    sanctions: SanctionsList = field(default_factory=SanctionsList)
    max_per_minute: int = 3
    killed: set[str] = field(default_factory=set)
    _recent: dict[str, list[float]] = field(default_factory=dict)
    _spent: dict[str, int] = field(default_factory=dict)  # token jti -> cents already moved
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # -- helpers ---------------------------------------------------------------------------
    def _deny(self, agent: str | None, intent: object, code: str, reason: str,
              policies: tuple[str, ...] = ()) -> Result:
        to = intent.get("to_iban") if isinstance(intent, dict) else None
        self.audit.append("DENIED", agent=agent, to=self.audit.tok(to), code=code, reason=reason,
                          policies=list(policies))
        return Result(Status.DENIED, reason, policies)

    @staticmethod
    def _validate(intent: object) -> str | None:
        if not isinstance(intent, dict) or set(intent) != INTENT_KEYS:
            return "intent must contain exactly: from, to_iban, amount_cents, currency"
        a = intent["amount_cents"]
        if isinstance(a, bool) or not isinstance(a, int):
            return "amount_cents must be an integer"
        if intent["currency"] not in ALLOWED_CURRENCIES:
            return "unsupported currency"
        iban = intent["to_iban"]
        if not isinstance(iban, str) or not iban.isascii():
            return "to_iban must be ASCII (look-alike characters rejected)"
        if not IBAN_RE.match(canonical_intent(intent)["to_iban"]):
            return "malformed IBAN"
        if not isinstance(intent["from"], str) or not intent["from"]:
            return "invalid source account"
        return None

    # -- main entry point ---------------------------------------------------------------------
    def transfer(self, token: str, intent: dict, approval: dict | None = None) -> Result:
        # Serialised: the budget / velocity / approval checks and their updates must be atomic,
        # otherwise concurrent requests could each see the same remaining budget.
        with self._lock:
            return self._transfer(token, intent, approval)

    def _transfer(self, token: str, intent: dict, approval: dict | None) -> Result:
        claims = self.ids.verify(token)
        if claims is None:
            return self._deny(None, intent, "authn", "invalid, expired or forged token")
        if (err := self._validate(intent)):
            return self._deny(claims.agent, intent, "schema", err)

        intent = canonical_intent(intent)
        iban, ih = intent["to_iban"], intent_hash(claims.agent, intent)
        now = time.time()
        recent = [t for t in self._recent.get(claims.agent, []) if now - t < 60]
        self._recent[claims.agent] = recent

        beneficiary = {
            "iban": iban,
            "registry_verified": "registry" in self.prov.origins(iban),
            "sanctioned": self.sanctions.is_sanctioned(iban),
        }
        ctx = {
            "amount_cents": intent["amount_cents"], "approval_valid": False,
            "source": intent["from"], "currency": intent["currency"],
            "killed": "ALL" in self.killed or claims.agent in self.killed,
            "velocity_exceeded": len(recent) >= self.max_per_minute,
            "task_max_cents": claims.max_amount_cents, "task_beneficiary": claims.beneficiary,
            "task_spent_cents": self._spent.get(claims.jti, 0),
            "task_source": claims.source, "task_currency": claims.currency,
        }
        scopes = list(claims.scopes)

        decision = self.pdp.decide(claims.agent, scopes, beneficiary, ctx)
        used_approval = False
        if not decision.allowed:
            with_approval = self.pdp.decide(claims.agent, scopes, beneficiary, {**ctx, "approval_valid": True})
            if with_approval.allowed:  # would be allowed if a valid human approval existed
                if approval is None:
                    self.audit.append("PENDING_APPROVAL", agent=claims.agent, hash=ih,
                                      amount_cents=intent["amount_cents"])
                    return Result(Status.PENDING_APPROVAL, "human approval required", (), ih)
                ok, why = self.approvals.verify(approval, ih)
                if not ok:
                    return self._deny(claims.agent, intent, "approval", why)
                used_approval, decision = True, with_approval
        if not decision.allowed:
            return self._deny(claims.agent, intent, "policy", decision.reason, decision.policies)

        if used_approval:
            self.approvals.consume(approval)  # type: ignore[arg-type]
        self.bank.transfer(self.credential, intent["from"], iban, intent["amount_cents"], intent["currency"])
        recent.append(now)
        self._spent[claims.jti] = ctx["task_spent_cents"] + intent["amount_cents"]
        self.audit.append("EXECUTED", agent=claims.agent, to=self.audit.tok(iban),
                          amount_cents=intent["amount_cents"], approver=(approval or {}).get("human") if used_approval else None,
                          hash=ih, policies=list(decision.policies))
        return Result(Status.EXECUTED, "ok", decision.policies, ih)
