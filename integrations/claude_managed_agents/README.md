# Claude Managed Agents integration

A Claude agent hosted by Anthropic (Claude Managed Agents) pays an invoice that hides a prompt injection.
The agent's only tools are **custom tools**: Anthropic sends each tool call to this script, which executes it.
So every transfer the agent proposes goes through `ToolGateway.transfer()` on your machine, and the agent never
holds a banking credential. This is the project's principle, with a production agent platform in front:
the agent proposes, the gateway decides.

```
Anthropic (agent loop, Claude)                 your machine (trusted)
  agent ── custom tool call ─────────────────▶  demo.py ─▶ ToolGateway (token, Cedar, budget, audit) ─▶ mock bank
        ◀── tool result: EXECUTED / DENIED ───
```

## Run it

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=...                                   # never commit it
python integrations/claude_managed_agents/demo.py setup        # once: creates the agent and environment
python integrations/claude_managed_agents/demo.py run
```

`setup` stores the agent and environment ids in `.managed_agent_ids.json` (git-ignored). Agents are persistent:
create once, reuse. `--model` picks the model at setup (default `claude-opus-5-5`).

## What you should see

The agent reads the invoice, proposes the legitimate 500 EUR payment, and the gateway executes it. A strong model
usually ignores the hidden instruction (in our runs Claude even flagged it to the user), so the run ends with a
clearly labelled **simulated hijack**: the attacker's intent, and a second payment of the same invoice, are sent
through the very same tool. Both are denied by Cedar rules. Only 500 EUR leaves the account.

## Design notes

- No agent toolset (bash, files, web) is enabled: the agent has exactly three tools.
- Managed Agents' own permission policies are not used for authorization: `auto` is evaluated by a model, and
  custom tools are not governed by them anyway. The deterministic gateway is the only decision point.
- Banking credentials never go to Anthropic (not in the agent, not in a vault): only the gateway holds them.
- Fictional data only.
