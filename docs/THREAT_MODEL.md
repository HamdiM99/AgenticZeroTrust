# Threat model

## Assets
Funds movable through the payment tool; beneficiary data (PII); integrity of the audit trail.

## Adversary
- Controls any **content** an agent reads (invoices, emails, web pages, tool outputs) => can attempt prompt injection.
- May fully **control the agent's output** (we assume compromise, we do not try to prevent it).
- Does **not** control: the control plane, signing keys, the beneficiary registry, human approvers' devices.

## Trust boundaries
Untrusted: LLM output, all ingested content, agent-supplied intent fields.
Trusted (assumed): Identity service, gateway, Cedar policies, provenance ingestion, registry, approvers.

## Threats and controls

| # | Threat | Control | Evidence (tests / eval) | Status |
|---|---|---|---|---|
| T1 | Indirect prompt injection redirects funds | Registry-only provenance + task-bound payee | `test_indirect_prompt_injection_in_document`, evals | Mitigated |
| T2 | Encoded / fragmented payloads (base64, split IBAN) | Provenance is by exact value; unknown => deny | evals `encoding` | Mitigated |
| T3 | Look-alike IBAN (homoglyph, typosquat) | ASCII-only schema; exact registry match | `test_homoglyph_iban_rejected_at_schema`, evals | Mitigated |
| T4 | Confused deputy (valid payee, wrong task; or another customer's account debited) | Token bound to one payee and one source account | `test_confused_deputy_*`, `test_source_account_bound_to_task` | Mitigated |
| T5 | Amount manipulation (incl. currency switch) | Task cap, hard cap, positive int cents, token bound to one currency | `test_amount_inflation_*`, `test_hard_cap_*`, `test_currency_bound_to_task` | Mitigated |
| T5b | Token replay / split payments | Task cap is a cumulative budget per token (`jti`), updated atomically | `test_token_replay_*`, `test_split_payments_*`, `test_concurrent_replay_*` | Mitigated (in-memory budget: see README limits) |
| T6 | Approval TOCTOU / replay / forgery / self-approval | Signature over op hash, single-use nonce, registered humans only | `test_toctou_*`, `test_approval_replay`, ... | Mitigated |
| T7 | Privilege escalation between agents | Scoped tokens, revocation honoured | `test_scope_escalation_*`, `test_tampered_token_*` | Mitigated |
| T8 | Bypass of the gateway | Credential held only by gateway | `test_cannot_bypass_gateway_to_core_bank` | Mitigated (in-process: see limits) |
| T9 | Runaway agent / abuse | Velocity limit, kill-switch | `test_velocity_limit`, `test_kill_switch` | Mitigated |
| T10 | Audit tampering, PII leak via logs | Hash chain, PII tokenisation | `test_audit.py` | Detect-only (tamper-evident, not tamper-proof) |
| T11 | Poisoned beneficiary registry / RAG memory | None | - | **Out of scope** |
| T12 | Compromise of the control plane itself | None beyond minimal size | - | **Out of scope** |
| T13 | Agent business-logic errors within its bounds | Bounded by task cap only | - | **Residual risk** |
| T14 | Approval fatigue | None | - | **Out of scope** (needs UX + threshold calibration) |

## What this does NOT claim
Not DORA/PCI/ISO compliant. Not a replacement for a bank's fraud engine. Does not detect prompt injection;
it makes injection **non-exploitable for the covered action**.
