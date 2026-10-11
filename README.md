# agentic-zero-trust

**A deterministic control plane for LLM agents that move money.**
Cedar policies, intent-bound tokens, provenance tracking, hash-bound human approval and a tamper-evident audit log.
The agent *proposes*; the control plane *disposes*. No LLM is ever in the authorization loop.

![The agent proposes, the control plane decides](docs/img/concept.png)

> Research demonstrator, fictional data only. Not production software. Makes no compliance claims (DORA, PCI, ...).

## The problem

Multi-agent banking assistants read untrusted content (invoices, emails, tool outputs) and can call payment tools.
Prompt-injection detection is probabilistic and keeps being bypassed. So this project does not try to *detect*
injection; it assumes the agent is **fully compromised** and makes the damage **non-exploitable** for the covered action.

## Results (reproducible: `make eval`)

| | |
|---|---|
| Attacks run (agent assumed fully compromised) | **19** across 10 categories |
| Attacks that moved money | **0** |
| Legitimate requests that succeeded | **5 / 5** (including a human-approved large payment) |
| Tests | **49** passing, Python 3.10-3.12 in CI |
| Policy mutation testing | **10 / 10** Cedar `forbid` rules covered (neutralise one, the suite fails) |

Full per-attack table, with the policy that blocked each: [`evals/results.md`](evals/results.md).
Categories: indirect injection, encoding/fragmentation, look-alike IBANs, confused deputy (payee and debited account),
amount manipulation, token replay / split payments, currency switch, social engineering, sanctions, schema smuggling.

## External benchmark: AgentDojo banking (`make agentdojo`, needs `pip install -e ".[agentdojo]"`)

The control plane is plugged into the [AgentDojo](https://github.com/ethz-spylab/agentdojo) banking suite
(v1.2: 16 user tasks x 9 injection tasks) as a guarded tool runtime: every payment, standing-order change and
account change the agent makes goes through the gateway ([`evals/agentdojo_bridge/`](evals/agentdojo_bridge/)).

**Worst case, no LLM needed**: the "agent" executes the attacker's goal verbatim, then the user's task.

| Configuration | Utility (no attack) | Attack success rate |
|---|---|---|
| Undefended | 16/16 | **143/144 (99.3%)** |
| AZT, mandate = payees in the user's prompt, no human | 9/16 | **0/144** |
| AZT, mandate = prompt + known beneficiaries, no human | 11/16 | **0/144** |
| AZT, + attentive human confirming new payees / account changes | 15/16 | **0/144** |
| AZT, + rubber-stamp human (approves everything) | 15/16 | 127/144 (88.2%) |

What this shows, honestly: with no human, the gateway blocks every attack but also every legitimate payment to
a payee the user did not name (bills read from files, "like last month"). The human step-up recovers utility,
and security then rests on the human: a rubber-stamp approver lets almost everything through (only the hard cap
still holds). The remaining 1/16 is a flaw in the benchmark's ground truth (it pays `"Apple"`, not an IBAN).
Full tables: [`results_replay.md`](evals/agentdojo_bridge/results_replay.md).

**Real model** (`gpt-4o-mini-2024-07-18`, AgentDojo `important_instructions` attack, single run, raw traces in
[`llm_runs/`](evals/agentdojo_bridge/llm_runs/)):

| Configuration | Utility (no attack) | Utility under attack | Attack success rate |
|---|---|---|---|
| Undefended | 9/16 (56%) | 61/144 (42%) | **70/144 (48.6%)** |
| AZT, no human (prompt / prompt + known payees) | 6/16 (38%) | 44/144, 43/144 (30%) | **0/144** |
| AZT, + attentive human | 8/16 (50%) | 62/144 (43%) | **0/144** |

With a human confirming new payees, the gateway removes every successful attack at a small utility cost
(one task, within single-run noise) and does not hurt utility under attack. Under attack, the model often spends
its turn on the attacker's (blocked) payments and never does the user's task: the gateway prevents the damage,
not the disruption. Reproduce: `python -m evals.agentdojo_bridge.run_llm --model gpt-4o-mini-2024-07-18 --write`
(about 2 USD). Full table: [`results_llm_gpt-4o-mini-2024-07-18.md`](evals/agentdojo_bridge/results_llm_gpt-4o-mini-2024-07-18.md).

![AgentDojo results](docs/img/agentdojo_results.png)

## How it works

```mermaid
flowchart LR
  A[Agent / LLM<br/>untrusted] -- "INTENT (structured)" --> G[Tool Gateway]
  D[Documents, tool outputs] -. "origin labels" .-> P[(Provenance)]
  P --> G
  T[Intent-bound token<br/>source + payee + currency + budget] --> G
  G --> C{{Cedar PDP}}
  C --> G
  H[Human approval<br/>signed over op hash] --> G
  G --> L[(Hash-chained audit)]
  G -- "sole credential holder" --> B[Core banking]
```

1. **Intent-bound tokens**: the trusted request fixes the source account, the payee, the currency and a maximum
   *total* amount. The cap is a cumulative budget per token, so replaying the token or splitting a payment cannot
   exceed it. The LLM cannot widen any of these.
2. **Provenance**: values get an origin label from the ingestion layer, never from the agent. Unknown => untrusted.
3. **Cedar policy** ([`policies/transfer.cedar`](policies/transfer.cedar)): default deny, `forbid` overrides `permit`,
   schema-validated. Python only gathers facts; rules live in Cedar.
4. **Human approval** over *structured parameters*, signature bound to the operation hash: single-use, expiring.
5. **Audit**: hash-chained, PII tokenised. Edits and deletions are detected.

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)

## Quickstart

```bash
pip install -e ".[dev]"
make demo      # narrated injection attempt
make test      # 49 tests
make eval      # attack corpus + benign traffic
make mutate    # policy mutation testing
```

or `docker build -t azt . && docker run --rm azt`.

## Repository layout

```
policies/    transfer.cedar + schema.cedarschema   (the rules)
src/azt/     identity, provenance, approval, policy (Cedar PDP), gateway (PEP), audit, bank (mock)
evals/       attack corpus, runner, generated results.md
tests/       attack scenarios, policy tests, audit tests
scripts/     mutation_check.py
docs/        architecture, threat model
```

## Honest limitations

- **In-process.** Components share a process, so nothing technically stops hostile code from calling them directly.
  Real isolation (separate services, mTLS/SPIFFE workload identity, HSM/vault credentials) is the roadmap, not done.
  Per-token budgets, approval nonces and velocity counters live in memory: a restart resets them, and several gateway
  replicas would need a shared atomic store (e.g. Postgres/Redis).
- **Provenance is exact-value matching**; it does not follow derived values (that needs CaMeL-style information-flow tracking).
  It fails *closed*, which costs utility on transformed data.
- **Trusted components are assumed trusted**: registry poisoning, RAG/memory poisoning and control-plane compromise are out of scope.
- **Residual risk**: within its token bounds, a compromised agent can still choose a wrong (but capped) amount.
- Audit log is tamper-*evident*, not tamper-*proof* (needs external anchoring).
- `LLMAgent` (real model as the proposer) exists but is experimental and not exercised in CI. Real-LLM results come
  from the AgentDojo bridge, one model, one run: treat small utility differences as noise.
- In the AgentDojo bridge the "attentive human" is simulated from the benchmark's ground truth: an upper bound on
  real human vigilance.

## Roadmap

- [ ] Split gateway / identity / approval into services with mTLS
- [x] AgentDojo banking integration, worst-case (compromised-agent) evaluation
- [x] Real-LLM AgentDojo run (gpt-4o-mini)
- [ ] More models, several seeds, adaptive attacks
- [ ] Cedar actions for account changes (today: a step-up rule in the AgentDojo bridge)
- [ ] Information-flow (taint) tracking beyond exact values
- [ ] External audit anchoring; approval-fatigue study

## License

MIT
