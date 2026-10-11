"""The Cedar policy itself: validated against its schema, and fail-closed on evaluation errors."""
from pathlib import Path

import cedarpy

from azt.policy import DEFAULT_DIR, CedarPDP

CTX = {"amount_cents": 100, "approval_valid": False, "killed": False, "velocity_exceeded": False,
       "source": "S", "currency": "EUR", "task_max_cents": 1000, "task_spent_cents": 0,
       "task_beneficiary": "X", "task_source": "S", "task_currency": "EUR"}
BEN = {"iban": "X", "registry_verified": True, "sanctioned": False}


def test_policies_validate_against_schema():
    p, s = Path(DEFAULT_DIR, "transfer.cedar").read_text(), Path(DEFAULT_DIR, "schema.cedarschema").read_text()
    assert cedarpy.validate_policies(p, s).validation_passed


def test_every_policy_has_a_reason_text():
    from azt.policy import REASON_TEXT
    pdp = CedarPDP()
    for pid in pdp._ids:
        if pid.startswith("forbid-"):
            assert pid in REASON_TEXT


def test_baseline_allow():
    assert CedarPDP().decide("a", ["transfer:create"], BEN, CTX).allowed


def test_no_scope_no_permit():
    d = CedarPDP().decide("a", [], BEN, CTX)
    assert not d.allowed and d.policies == ()


def test_forbid_overrides_permit():
    d = CedarPDP().decide("a", ["transfer:create"], {**BEN, "sanctioned": True}, CTX)
    assert not d.allowed and "forbid-sanctioned" in d.policies


def test_fail_closed_on_bad_context():
    d = CedarPDP().decide("a", ["transfer:create"], BEN, {**CTX, "amount_cents": "not-a-number"})
    assert not d.allowed


def test_task_cap_counts_what_was_already_spent():
    pdp = CedarPDP()
    assert pdp.decide("a", ["transfer:create"], BEN, {**CTX, "task_spent_cents": 900}).allowed
    d = pdp.decide("a", ["transfer:create"], BEN, {**CTX, "task_spent_cents": 901})
    assert not d.allowed and "forbid-over-task-cap" in d.policies
