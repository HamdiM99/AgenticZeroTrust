from azt.sandbox import ATTACKER, GOOD, intent


def test_chain_verifies_then_detects_tampering(w):
    w.gw.transfer(w.token(), intent())
    w.gw.transfer(w.token(), intent(to=ATTACKER))
    assert w.audit.verify() == (True, None)
    w.audit.entries[0]["data"]["amount_cents"] = 1
    ok, idx = w.audit.verify()
    assert not ok and idx == 0


def test_deleting_an_entry_is_detected(w):
    for _ in range(3):
        w.gw.transfer(w.token(), intent(amount_cents=10))
    del w.audit.entries[1]
    assert w.audit.verify()[0] is False


def test_no_raw_iban_in_logs(w):
    w.gw.transfer(w.token(), intent())
    w.gw.transfer(w.token(), intent(to=ATTACKER))
    dump = w.audit.to_jsonl()
    assert GOOD not in dump and ATTACKER not in dump
