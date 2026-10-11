from evals.run_eval import run


def test_no_attack_executes_and_benign_traffic_flows():
    attacks, benign = run()
    assert all(r[4] == 0 for r in attacks), [r for r in attacks if r[4] > 0]
    assert all(r[1] == "EXECUTED" for r in benign), benign
