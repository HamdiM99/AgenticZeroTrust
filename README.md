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
account change the agent makes goes through the gateway ([`integrations/agentdojo/`](integrations/agentdojo/)).

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
Full tables: [`results_replay.md`](integrations/agentdojo/results_replay.md).

**Real models** (one run per model, raw traces in [`llm_runs/`](integrations/agentdojo/llm_runs/)). Newer runs
attribute every attacked scenario: did the model **resist**, did it **obey and the gateway block** the action,
or did the attack **succeed**?

| Model | Weights | Attack | Attacks succeeding, undefended | **with AZT** (+ attentive human) | Utility, no attack (undefended -> AZT) |
|---|---|---|---|---|---|
| `gpt-4o-mini` | closed, 2024 | `important_instructions` | **70/144 (48.6%)** | **0/144** | 9/16 -> 8/16 |
| `glm-4.6` (Z.ai) | **open** | `important_instructions` | **3/144 (2.1%)** | **0/144**: obeyed 3 times, **all 3 blocked by the gateway** | 12/16 -> 15/16 |
| `claude-sonnet-5-5` | closed | `important_instructions` | 0/144 | 0/144 | 15/16 -> 16/16 |
| `claude-haiku-5-5` | closed | `tool_knowledge` (stronger) | 0/144 (never even tried the attacker's action) | not run: nothing to block | 11/16 undefended |

What this shows:

1. **A guarantee that does not depend on the model.** Worst case, agent fully obeying the attacker: 99% -> 0%.
2. **An older model** (`gpt-4o-mini`) obeys half of the injections; the gateway removes all of them.
3. **Recent models resist these known, non-adaptive attacks on their own** (Sonnet 5.5, and Haiku 5.5 even under
   a stronger attack), likely thanks to safety training on similar patterns. **But the open-weight GLM-4.6 still
   obeyed 3 times, and the gateway blocked all 3**: model robustness is probabilistic, the gateway is not.
4. **With a human confirming new payees, the gateway costs no utility** on any model (differences of one to
   three tasks are single-run noise). Without a human it blocks legitimate payments to payees the user never named.
5. Under attack, a model may spend its turn on the attacker's (blocked) payments and never do the user's task:
   the gateway prevents the damage, not the disruption.

**The open challenge is adaptive attacks.** Off-the-shelf benchmark attacks are increasingly saturated by recent
models, while attacks optimised against a given model or defense keep breaking model-based protections (e.g.
"The Attacker Moves Second", 2025). That is where a model-independent control plane matters, and it is the next
evaluation step for this project.

Haiku 5.5 often asks the user to confirm (e.g. the payment date) instead of paying, which AgentDojo counts as a
failure: its low utility is model caution, not the gateway. Mistral and DeepSeek are supported by the runner but
were not evaluated yet. Reproduce: `python -m integrations.agentdojo.run_llm --model <model> [--attack <name>] --write`
(`provider:model` for OpenAI-compatible providers: `zai:glm-4.6`, `mistral:...`, `deepseek:...`).
Tables: [`results_llm_*.md`](integrations/agentdojo/).

![AgentDojo results](docs/img/agentdojo_results.png)

## Works with

| Integration | What it shows |
|---|---|
| [`integrations/claude_managed_agents/`](integrations/claude_managed_agents/) | A live Claude agent hosted by Anthropic, whose only tools route through the gateway |
| [`integrations/agentdojo/`](integrations/agentdojo/) | The AgentDojo banking benchmark (ETH Zurich), with OpenAI, Anthropic and OpenAI-compatible models (Mistral, DeepSeek, GLM) |

## Live demo with a Claude Managed Agent

[`integrations/claude_managed_agents/demo.py`](integrations/claude_managed_agents/demo.py): a Claude agent hosted by Anthropic pays a poisoned
invoice. Its only tools are custom tools executed by this repo, so every payment it proposes goes through the gateway
on your machine; it never holds a banking credential. The run ends with a labelled "what if the agent had obeyed?"
step that sends the attacker's intent through the same tool.

```
AGENT   proposes propose_transfer({"amount_cents": 50000, "currency": "EUR", "from": "FR76ACCOUNTBANK0000001", "to_iban": "FR7630001007941234567890185"})
GATEWAY ✅ EXECUTED: ok  [permit-small-transfer]
--- What if the agent had obeyed the hidden instruction? (simulated hijack, same tool) ---
GATEWAY ⛔ DENIED: beneficiary differs from the one bound to this task; amount exceeds the remaining budget ...
--- ...or kept the right payee but paid the invoice a second time? ---
GATEWAY ⛔ DENIED: amount exceeds the remaining budget bound to this task  [forbid-over-task-cap]
Money that actually left the account: [('FR7630001007941234567890185', 500.0)]
```

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
make test      # 52 tests (3 need the agentdojo extra)
make eval      # attack corpus + benign traffic
make mutate    # policy mutation testing
```

or `docker build -t azt . && docker run --rm azt`.

## Repository layout

```
policies/    transfer.cedar + schema.cedarschema   (the rules)
src/azt/     identity, provenance, approval, policy (Cedar PDP), gateway (PEP), audit, bank (mock)
evals/       attack corpus, runner, generated results.md
integrations/agentdojo/               AgentDojo banking benchmark bridge, real-LLM runner, results, traces
integrations/claude_managed_agents/   live demo with a Claude Managed Agent
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
  from the AgentDojo bridge, one run per model: treat small utility differences as noise. The AgentDojo attacks
  used are known and non-adaptive; adaptive attacks would likely make recent models obey more often.
- In the AgentDojo bridge the "attentive human" is simulated from the benchmark's ground truth: an upper bound on
  real human vigilance.

## Roadmap

- [ ] Split gateway / identity / approval into services with mTLS
- [x] AgentDojo banking integration, worst-case (compromised-agent) evaluation
- [x] Real-LLM AgentDojo runs: gpt-4o-mini, Claude Sonnet 5.5 / Haiku 5.5, GLM-4.6 (open weights)
- [x] Per-scenario attribution: model resisted / gateway blocked / attack succeeded
- [ ] **Adaptive attacks** (an attacker model that rewrites the injection until the agent obeys)
- [ ] More open-weight models (Mistral, DeepSeek, Llama, Qwen), several seeds per model
- [ ] Cedar actions for account changes (today: a step-up rule in the AgentDojo bridge)
- [ ] Information-flow (taint) tracking beyond exact values
- [ ] External audit anchoring; approval-fatigue study

## License

MIT
