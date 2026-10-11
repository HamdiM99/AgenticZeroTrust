"""Mock core banking. Only the gateway holds the credential; agents never see it."""
from __future__ import annotations

import hmac
from dataclasses import dataclass


@dataclass(frozen=True)
class Transfer:
    source: str
    to_iban: str
    amount_cents: int
    currency: str


class CoreBank:
    def __init__(self, credential: str) -> None:
        self._credential = credential
        self.ledger: list[Transfer] = []

    def transfer(self, credential: str, source: str, to_iban: str, amount_cents: int, currency: str) -> None:
        if not hmac.compare_digest(credential, self._credential):
            raise PermissionError("invalid core-banking credential")
        self.ledger.append(Transfer(source, to_iban, amount_cents, currency))
