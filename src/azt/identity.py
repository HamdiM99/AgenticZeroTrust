"""Agent identity + intent-bound capability tokens.

A token is short-lived, signed, and bound to ONE task: a source account, a beneficiary, a currency
and a maximum TOTAL amount, all fixed by the trusted side (the authenticated user's request), never
by the LLM. The cap is a cumulative budget for the token (tracked by the gateway via `jti`), not a
per-transfer limit, so a token cannot be replayed or split to move more than the task allows.
Production note: replace HMAC with asymmetric signatures / SPIFFE-mTLS workload identity.
"""
from __future__ import annotations

import hmac
import json
import secrets
import time
from dataclasses import dataclass

from .util import canon, norm_iban, sign


@dataclass(frozen=True)
class Claims:
    agent: str
    task: str
    scopes: tuple[str, ...]
    max_amount_cents: int
    beneficiary: str
    source: str
    currency: str
    jti: str
    exp: float


class IdentityService:
    def __init__(self) -> None:
        self._key = secrets.token_bytes(32)
        self.agents: dict[str, set[str]] = {}

    def register(self, agent: str, scopes: list[str]) -> None:
        self.agents[agent] = set(scopes)

    def revoke(self, agent: str) -> None:
        self.agents.pop(agent, None)

    def issue(self, agent: str, task: str, *, max_amount_cents: int, beneficiary: str, source: str,
              currency: str, ttl: int = 60) -> str:
        payload = canon({
            "agent": agent, "task": task, "scopes": sorted(self.agents[agent]),
            "max_amount_cents": max_amount_cents, "beneficiary": norm_iban(beneficiary),
            "source": norm_iban(source), "currency": currency,
            "exp": time.time() + ttl, "jti": secrets.token_hex(16),
        })
        return payload + "." + sign(self._key, payload)

    def verify(self, token: str) -> Claims | None:
        try:
            payload, sig = token.rsplit(".", 1)
            if not hmac.compare_digest(sig, sign(self._key, payload)):
                return None
            c = json.loads(payload)
            if c["exp"] < time.time() or c["agent"] not in self.agents:
                return None
            scopes = tuple(sorted(set(c["scopes"]) & self.agents[c["agent"]]))  # honours revocation
            return Claims(c["agent"], c["task"], scopes, c["max_amount_cents"], c["beneficiary"],
                          c["source"], c["currency"], c["jti"], c["exp"])
        except (ValueError, KeyError, TypeError):  # malformed token => unauthenticated
            return None
