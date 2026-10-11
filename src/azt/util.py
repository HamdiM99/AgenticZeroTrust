"""Small deterministic helpers shared by all components."""
from __future__ import annotations

import hashlib
import hmac
import json
import re

IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")


def h(x: str | bytes) -> str:
    return hashlib.sha256(x.encode() if isinstance(x, str) else x).hexdigest()


def canon(d: object) -> str:
    """Canonical JSON: stable key order, no whitespace."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def sign(key: bytes, msg: str) -> str:
    return hmac.new(key, msg.encode(), hashlib.sha256).hexdigest()


def norm_iban(v: object) -> str:
    """Strip whitespace and upper-case. Deliberately NOT Unicode-folding: look-alikes stay distinct."""
    return re.sub(r"\s+", "", str(v)).upper()


def canonical_intent(intent: dict) -> dict:
    out = dict(intent)
    for k in ("from", "to_iban"):
        if isinstance(out.get(k), str):
            out[k] = norm_iban(out[k])
    return out
