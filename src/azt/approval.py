"""Human approval bound to the exact operation (anti-TOCTOU), single-use, expiring.

The approver signs a hash over the canonical STRUCTURED parameters, never an LLM-written summary.
Production note: signing keys live on the approver's device/HSM, not in this service.
"""
from __future__ import annotations

import hmac
import secrets
import time

from .util import canon, canonical_intent, h, sign


def intent_hash(agent: str, intent: dict) -> str:
    return h(canon({**canonical_intent(intent), "agent": agent}))


class ApprovalService:
    def __init__(self, humans: dict[str, bytes]) -> None:
        self._humans = humans
        self._used: set[str] = set()

    @staticmethod
    def render(agent: str, intent: dict) -> str:
        """What the human is shown: the exact parameters that will be executed."""
        return canon({**canonical_intent(intent), "agent": agent})

    def approve(self, human: str, agent: str, intent: dict, ttl: int = 300) -> dict:
        ih, nonce, exp = intent_hash(agent, intent), secrets.token_hex(16), time.time() + ttl
        return {"human": human, "hash": ih, "nonce": nonce, "exp": exp,
                "sig": sign(self._humans[human], f"{ih}|{nonce}|{exp}")}

    def verify(self, a: dict, ih: str) -> tuple[bool, str]:
        """Check without consuming; the gateway consumes only when the approval is actually used."""
        try:
            key = self._humans.get(a["human"])
            if key is None:
                return False, "approver is not a registered human"
            if not hmac.compare_digest(a["sig"], sign(key, f"{a['hash']}|{a['nonce']}|{a['exp']}")):
                return False, "invalid approval signature"
            if a["exp"] < time.time():
                return False, "approval expired"
            if a["hash"] != ih:
                return False, "operation differs from what was approved (TOCTOU)"
            if a["nonce"] in self._used:
                return False, "approval already consumed (replay)"
            return True, "ok"
        except (KeyError, TypeError):
            return False, "malformed approval"

    def consume(self, a: dict) -> None:
        self._used.add(a["nonce"])
